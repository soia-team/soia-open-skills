#!/usr/bin/env python3
"""scan_drive.py — 只读 DFS 扫描阿里云盘目录树 → JSONL（喂给 alipan-curator 的 gen_catalog.py）。

仅用 read-only `aliyunpan ll --driveId <id> <path>`，不做任何写操作。
线程池并发 + 每调用重试 + 断点续扫(--resume) + 可选聚合剪枝(海量碎片区) + 敏感目录只记不下钻。

用法：
  scan_drive.py --driveId ID --root /A [--root /B ...] --out scan.jsonl
                [--workers 6 --resume --no-descend 目录名
                 --agg-prefix /A/碎片区 --agg-threshold 200 --agg-min-depth 3]

输出 JSONL 每行（gen_catalog.py 直接吃）：
  {"path": <父目录>, "name": <名>, "id": <file_id>, "dir": true/false, "size": <字节或null>
   [, "agg_files": N, "agg_size": 字节]}   # 聚合行：碎片区某目录只记文件数/总大小不逐列
扫描根自身不入 JSONL（其 file_id 另用 roots.json 提供给 gen_catalog）。
错误/进度写 <out>.errors / <out>.progress。被 kill 后加 --resume 重跑接着扫。
"""
import argparse, json, os, queue, re, subprocess, threading, time

from soia_env import load_private_env

load_private_env(required=False)

ROW = re.compile(r"\s{2,}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--driveId', required=True)
    ap.add_argument('--root', action='append', required=True, dest='roots')
    ap.add_argument('--out', required=True)
    ap.add_argument('--workers', type=int, default=6)
    ap.add_argument('--timeout', type=int, default=90)
    ap.add_argument('--attempts', type=int, default=3)
    ap.add_argument('--resume', action='store_true')
    ap.add_argument('--no-descend', action='append', default=[], help='目录名，扫到只记录不进入(隐私)')
    ap.add_argument('--agg-prefix', default='', help='此前缀下的碎片区启用聚合剪枝')
    ap.add_argument('--agg-threshold', type=int, default=200)
    ap.add_argument('--agg-min-depth', type=int, default=3, help='相对扫描根的深度(根=0)')
    a = ap.parse_args()
    err_p, prog_p = a.out + '.errors', a.out + '.progress'

    done = set()
    if a.resume and os.path.exists(a.out):
        for line in open(a.out):
            try: done.add(json.loads(line).get('path'))
            except: pass

    lock = threading.Lock()
    jf = open(a.out, 'a'); ef = open(err_p, 'a')
    cnt = {'dirs': 0, 'files': 0, 'agg': 0, 'errors': 0, 'calls': 0}
    tq = queue.Queue()

    def emit(o):
        with lock: jf.write(json.dumps(o, ensure_ascii=False) + '\n'); jf.flush()
    def logerr(m):
        with lock:
            ef.write(f"[{time.strftime('%H:%M:%S')}] {m}\n"); ef.flush(); cnt['errors'] += 1

    def run_ll(path):
        last = 'unknown'
        for att in range(1, a.attempts + 1):
            with lock: cnt['calls'] += 1
            try:
                r = subprocess.run(['aliyunpan', 'll', '--driveId', a.driveId, path],
                                   capture_output=True, text=True, timeout=a.timeout)
                if r.returncode == 0 and '当前目录' in r.stdout: return r.stdout
                last = f"rc={r.returncode} {r.stdout[:200]!r}"
            except Exception as e:
                last = repr(e)
            if att < a.attempts: time.sleep(1.5 * att)
        logerr(f"LIST_FAIL {path!r} {last}"); return None

    def parse(out):
        rows = []
        for raw in out.splitlines():
            ln = raw.strip()
            if not ln or ln.startswith('当前目录') or ln.startswith('----'): continue
            if '总:' in ln and '文件总数' in ln: continue
            p = ROW.split(ln)
            if not p or p[0] == '#': continue
            try: int(p[0])
            except ValueError: continue
            if len(p) < 8: continue
            nf = ' '.join(p[7:]) if len(p) > 8 else p[7]
            isdir = nf.endswith('/'); name = nf[:-1] if isdir else nf
            size = None
            if not isdir:
                try: size = int(p[4])
                except (ValueError, TypeError): size = None
            rows.append({'id': p[1], 'name': name, 'dir': isdir, 'size': size})
        return rows

    def worker():
        while True:
            try: path, depth, inagg = tq.get(timeout=2)
            except queue.Empty: return
            try:
                with lock:
                    open(prog_p, 'w').write(
                        f"calls={cnt['calls']} dirs={cnt['dirs']} files={cnt['files']} "
                        f"agg={cnt['agg']} errors={cnt['errors']} q={tq.qsize()} cur={path}\n")
                out = run_ll(path)
                if out is None: continue
                rows = parse(out)
                dirs = [e for e in rows if e['dir']]; files = [e for e in rows if not e['dir']]
                nowagg = inagg or bool(a.agg_prefix) and (path == a.agg_prefix or path.startswith(a.agg_prefix + '/'))
                if a.agg_prefix and nowagg and depth >= a.agg_min_depth and len(files) > a.agg_threshold:
                    emit({'path': path.rsplit('/', 1)[0] or '/', 'name': path.rsplit('/', 1)[-1],
                          'id': None, 'dir': True, 'size': None,
                          'agg_files': len(files), 'agg_size': sum((f['size'] or 0) for f in files)})
                    with lock: cnt['agg'] += 1
                else:
                    for f in files:
                        emit({'path': path, 'name': f['name'], 'id': f['id'], 'dir': False, 'size': f['size']})
                        with lock: cnt['files'] += 1
                for d in dirs:
                    emit({'path': path, 'name': d['name'], 'id': d['id'], 'dir': True, 'size': None})
                    with lock: cnt['dirs'] += 1
                    if d['name'] in a.no_descend: continue          # 隐私：记录但不下钻
                    dpath = path + '/' + d['name']
                    if a.resume and dpath in done: continue          # 断点续扫：已扫过的跳过
                    tq.put((dpath, depth + 1, nowagg))
            finally:
                tq.task_done()

    for r in a.roots: tq.put((r.rstrip('/'), 0, False))
    ts = [threading.Thread(target=worker, daemon=True) for _ in range(a.workers)]
    for t in ts: t.start()
    tq.join()
    jf.close(); ef.close()
    print(f"DONE dirs={cnt['dirs']} files={cnt['files']} agg={cnt['agg']} errors={cnt['errors']} calls={cnt['calls']}")

if __name__ == '__main__': main()
