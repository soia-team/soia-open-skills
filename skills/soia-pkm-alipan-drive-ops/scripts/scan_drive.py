#!/usr/bin/env python3
"""scan_drive.py — 只读 DFS 扫描阿里云盘目录树 → JSONL（喂给 alipan-curator 的 gen_catalog.py）。

仅用 read-only `aliyunpan ll --driveId <id> <path>`，不做任何写操作。
线程池并发 + 每调用重试 + 断点续扫(--resume) + 可选聚合剪枝(海量碎片区) + 敏感目录只记不下钻。

用法：
  scan_drive.py --driveId ID --root /A [--root /B ...] --out scan.jsonl
                [--workers 6 --resume --no-descend 目录名
                 --agg-prefix /A/碎片区 --agg-threshold 200 --agg-min-depth 3]

输出 JSONL 每行（gen_catalog.py 直接吃）：
  {"path": <父目录>, "name": <名>, "id": <file_id>, "dir": true/false,
   "size": <字节或null>, "sha1": <文件SHA-1或null>}
   [, "agg_files": N, "agg_size": 字节]}   # 聚合行：碎片区某目录只记文件数/总大小不逐列
扫描根自身不入 JSONL（其 file_id 另用 roots.json 提供给 gen_catalog）。
错误/进度写 <out>.errors / <out>.progress；已完整列出的目录逐行记入 <out>.done(断点续扫的权威依据，
旧格式扫描无此文件时退回 JSONL 启发式并自动迁移)。被 kill 后加 --resume 重跑接着扫。
"""
import argparse, json, os, queue, subprocess, sys, threading, time
from pathlib import Path

RUNNER_ENV = "SOIA_ALIPAN_RUNNER"


def alipan_runner_path():
    """Locate this skill's private-environment runner without a bare fallback."""
    override = os.environ.get(RUNNER_ENV)
    candidate = (
        Path(override).expanduser()
        if override
        else Path(__file__).resolve().with_name("run_with_env.py")
    )
    return candidate if candidate.is_file() else None


def require_alipan_runner():
    """Return the runner or fail before the scan creates any output files."""
    runner = alipan_runner_path()
    if runner is None:
        raise FileNotFoundError(
            "aliyunpan environment runner unavailable; set SOIA_ALIPAN_RUNNER "
            "or install this skill's scripts/run_with_env.py"
        )
    return runner


def run_aliyunpan_ll(runner, drive_id, path, timeout):
    """List one directory only through the private-environment runner."""
    args = [
        sys.executable,
        str(runner),
        "--",
        "aliyunpan",
        "ll",
        "--driveId",
        drive_id,
        path,
    ]
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout)

def parse_ll_output(out):
    """Parse ``aliyunpan ll`` without normalizing whitespace in file names.

    The table has nine fields before the name. ``split(None, 9)`` consumes only
    those fields and leaves the tenth field untouched, so names containing
    repeated spaces remain byte-for-byte usable as the next ``ll`` path.
    """
    rows = []
    for raw in out.splitlines():
        line = raw.strip()
        if not line or line.startswith('当前目录') or line.startswith('----'):
            continue
        if '总:' in line and '文件总数' in line:
            continue
        parts = line.split(None, 9)
        if not parts or parts[0] == '#':
            continue
        try:
            int(parts[0])
        except ValueError:
            continue
        if len(parts) < 10:
            continue
        name_field = parts[9]
        isdir = name_field.endswith('/')
        name = name_field[:-1] if isdir else name_field
        size = None
        if not isdir:
            try:
                size = int(parts[4])
            except (ValueError, TypeError):
                size = None
        sha1 = None if parts[3] == '-' else parts[3]
        rows.append({
            'id': parts[1],
            'name': name,
            'dir': isdir,
            'size': size,
            'sha1': sha1,
        })
    return rows


def row_identity(row):
    """Return the stable physical key used to compact scan JSONL rows.

    ``path`` is the parent directory in scan output.  ``id`` distinguishes
    separate cloud objects that happen to share a logical parent/name path;
    mutable metadata such as size and SHA-1 must not split one physical row.
    """
    return (row.get('path'), row.get('name'), row.get('id'), row.get('dir'))

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
    runner = require_alipan_runner()
    err_p, prog_p, done_p = a.out + '.errors', a.out + '.progress', a.out + '.done'

    # resume 重建：done=已完整列出的目录；dirseen=所有已发现的子目录；aggdone=聚合目录(故意不下钻)。
    # done 权威来源是 <out>.done sidecar(一行一目录，目录全部 emit+入队后才落盘)；无 sidecar 的旧格式
    # 扫描退回 JSONL 启发式(path 出现过≈列出过，撕裂列表不可辨)，并把启发式结果一次性写入新建
    # sidecar 完成迁移。前沿 = dirseen - done - aggdone：已发现但从未列出的目录必须重新入队。
    done, dirseen, aggdone = set(), set(), set()
    has_sidecar = os.path.exists(done_p)
    if a.resume and has_sidecar:
        for line in open(done_p):
            p = line.rstrip('\n')                            # 只去换行：目录名可含首尾空格
            if p: done.add(p)
    if a.resume and os.path.exists(a.out):
        for line in open(a.out):
            try: o = json.loads(line)
            except: continue                                 # 撕裂行：其父目录必不在 done，会被重扫补回
            if not isinstance(o, dict): continue
            if not has_sidecar: done.add(o.get('path'))      # 旧格式启发式：发过子行≈列出过
            if not o.get('dir') or not o.get('name'): continue
            dp = str(o.get('path')) + '/' + str(o.get('name'))   # 与 worker 里 dpath 拼法一致
            if 'agg_files' in o: aggdone.add(dp)             # 聚合行：该目录已按聚合语义记账，不重列
            elif o.get('name') not in a.no_descend: dirseen.add(dp)
    if a.resume and not has_sidecar and done:
        with open(done_p, 'w') as seed:                      # 迁移种子：启发式 done 落盘，此后以 sidecar 为准
            seed.writelines(p + '\n' for p in sorted(x for x in done if isinstance(x, str)))

    lock = threading.Lock()
    jf = open(a.out, 'a'); ef = open(err_p, 'a'); df = open(done_p, 'a')
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
                r = run_aliyunpan_ll(runner, a.driveId, path, a.timeout)
                if r.returncode == 0 and '当前目录' in r.stdout: return r.stdout
                last = f"rc={r.returncode} {r.stdout[:200]!r}"
            except Exception as e:
                last = repr(e)
            if att < a.attempts: time.sleep(1.5 * att)
        logerr(f"LIST_FAIL {path!r} {last}"); return None

    def worker():
        while True:
            try: path, depth, inagg = tq.get(timeout=2)
            except queue.Empty: return
            if path in done: tq.task_done(); continue        # 已列出过的目录不重列、不重发子行
            try:
                with lock:
                    open(prog_p, 'w').write(
                        f"calls={cnt['calls']} dirs={cnt['dirs']} files={cnt['files']} "
                        f"agg={cnt['agg']} errors={cnt['errors']} q={tq.qsize()} cur={path}\n")
                out = run_ll(path)
                if out is None: continue
                rows = parse_ll_output(out)
                dirs = [e for e in rows if e['dir']]; files = [e for e in rows if not e['dir']]
                nowagg = inagg or bool(a.agg_prefix) and (path == a.agg_prefix or path.startswith(a.agg_prefix + '/'))
                if a.agg_prefix and nowagg and depth >= a.agg_min_depth and len(files) > a.agg_threshold:
                    emit({'path': path.rsplit('/', 1)[0] or '/', 'name': path.rsplit('/', 1)[-1],
                          'id': None, 'dir': True, 'size': None,
                          'agg_files': len(files), 'agg_size': sum((f['size'] or 0) for f in files)})
                    with lock: cnt['agg'] += 1
                else:
                    for f in files:
                        emit({'path': path, 'name': f['name'], 'id': f['id'], 'dir': False,
                              'size': f['size'], 'sha1': f['sha1']})
                        with lock: cnt['files'] += 1
                for d in dirs:
                    emit({'path': path, 'name': d['name'], 'id': d['id'], 'dir': True,
                          'size': None, 'sha1': None})
                    with lock: cnt['dirs'] += 1
                    if d['name'] in a.no_descend: continue          # 隐私：记录但不下钻
                    dpath = path + '/' + d['name']
                    if a.resume and dpath in done: continue          # 断点续扫：已扫过的跳过
                    tq.put((dpath, depth + 1, nowagg))
                with lock: df.write(path + '\n'); df.flush() # 该目录全部 emit+入队完毕，落盘断点(空目录也记)
            finally:
                tq.task_done()

    for r in a.roots:
        rp = r.rstrip('/')
        if a.resume and rp in done: continue                 # 该根上次已列出，其子树由下面的前沿重建接管
        tq.put((rp, 0, False))
    if a.resume:
        rootps = sorted({r.rstrip('/') for r in a.roots}, key=len, reverse=True)
        for p in sorted(dirseen - done - aggdone):
            rp = next((r for r in rootps if p.startswith(r + '/')), None)
            if rp is None: continue                          # 不在当前 roots 之下的历史行不入队
            inagg = bool(a.agg_prefix) and (p == a.agg_prefix or p.startswith(a.agg_prefix + '/'))
            tq.put((p, p[len(rp):].count('/'), inagg))       # 深度=相对所属根的路径段数(根=0)
    ts = [threading.Thread(target=worker, daemon=True) for _ in range(a.workers)]
    for t in ts: t.start()
    tq.join()
    jf.close(); ef.close(); df.close()
    print(f"DONE dirs={cnt['dirs']} files={cnt['files']} agg={cnt['agg']} errors={cnt['errors']} calls={cnt['calls']}")

if __name__ == '__main__': main()
