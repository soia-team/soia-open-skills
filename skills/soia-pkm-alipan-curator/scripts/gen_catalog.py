#!/usr/bin/env python3
"""catalog 工作流：从全盘扫描 JSONL 生成「折叠树标题 + 资源级表格」的馆藏总览。

通用、无私有数据硬编码。用法：
  gen_catalog.py --scan-dir DIR --out FILE [--moves f] [--deletes f] [--roots f] [--title T]

JSONL 每行：{"path","name","id","dir","size"[,"agg_files","agg_size"]}
约定：整理时的分类夹带 `NN_` 数字前缀（10_/20_…），真实资源用原名。
渲染：分类夹 → 可折叠标题（#/##/###/…）；第一个非 NN_ 目录 → 表格一行（资源名+🔗直达+媒介+文件数+大小）。
点资源行的 🔗 即到网盘看文件，故总览本身不铺文件、保持清爽。
"""
import json, re, argparse, os
from collections import defaultdict, Counter
NN = re.compile(r'^\d{2}[_.]')
FOLDER_URL = "https://www.alipan.com/drive/folder/"
VID={'mp4','mkv','avi','flv','rmvb','mov','ts','wmv','m4v','mpg','vob'}
AUD={'mp3','wma','m4a','flac','wav','ape'}; DOC={'pdf','doc','docx','ppt','pptx','epub','txt','azw3','mobi','xls','xlsx'}; IMG={'jpg','jpeg','png','gif','bmp','webp'}

def human(n):
    n=n or 0
    for u in ['B','KB','MB','GB','TB']:
        if n<1024: return (f"{int(n)}B" if u=='B' else f"{n:.1f}{u}")
        n/=1024
    return f"{n:.1f}PB"

def load(scan_dir, moves_f, del_f, roots_f):
    recs={}
    for fn in sorted(os.listdir(scan_dir)):
        if not fn.endswith('.jsonl'): continue
        for line in open(os.path.join(scan_dir,fn)):
            line=line.strip()
            if not line: continue
            try: r=json.loads(line)
            except: continue
            if not isinstance(r,dict) or 'path' not in r: continue
            p=r['path'].rstrip('/')
            if not r.get('name'): r['name']=p.rsplit('/',1)[-1]
            if r.get('name') and p.rsplit('/',1)[-1]!=r['name']:
                p=p+'/'+r['name']; r={**r,'path':p}
            if p in recs and 'new' in fn.lower(): continue
            recs[p]=r
    if roots_f and os.path.exists(roots_f):
        for p,fid in json.load(open(roots_f)).items():
            if p not in recs or not recs[p].get('id'):
                recs[p]={'path':p,'name':p.rsplit('/',1)[-1],'id':fid,'dir':True,'size':None}
    if del_f and os.path.exists(del_f):
        for pref in json.load(open(del_f)).get('deleted_prefixes',[]):
            for k in [k for k in recs if k==pref or k.startswith(pref+'/')]: del recs[k]
    if moves_f and os.path.exists(moves_f):
        for line in open(moves_f):
            m=json.loads(line); t=m.get('type')
            if t=='mv' and m.get('old') and m.get('new'):
                old,new=m['old'].rstrip('/'),m['new'].rstrip('/')
                if new in recs and recs[new].get('dir') and new.rsplit('/',1)[-1]!=old.rsplit('/',1)[-1]:
                    new=new+'/'+old.rsplit('/',1)[-1]
                for k in [k for k in recs if k==old or k.startswith(old+'/')]:
                    nk=new+k[len(old):]; recs[nk]={**recs[k],'path':nk,'name':nk.rsplit('/',1)[-1]}; del recs[k]
            elif t=='rmdir' and (m.get('old') or m.get('path')):
                old=(m.get('old') or m.get('path')).rstrip('/')
                for k in [k for k in recs if k==old or k.startswith(old+'/')]: del recs[k]
            elif t=='mkdir' and m.get('new'):
                p=m['new'].rstrip('/')
                if p not in recs: recs[p]={'path':p,'name':p.rsplit('/',1)[-1],'id':None,'dir':True,'size':None}
    return recs

def build(recs):
    ch=defaultdict(list)
    for p in recs:
        par=p.rsplit('/',1)[0] if p.count('/')>1 else ''
        ch[par].append(p)
    # 健壮性：凡有子节点的路径必是目录（纠正扫描误标的 dir=false）
    for parent in list(ch):
        if parent and parent in recs: recs[parent]['dir']=True
    for v in ch.values(): v.sort(key=lambda p:(not recs[p].get('dir'), recs[p]['name']))
    return ch

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--scan-dir',required=True); ap.add_argument('--out',required=True)
    ap.add_argument('--moves'); ap.add_argument('--deletes'); ap.add_argument('--roots')
    ap.add_argument('--title',default='云盘馆藏总览'); ap.add_argument('--drive',default='备份盘')
    ap.add_argument('--search-dir',help='额外输出:按区分的全文检索索引目录(每文件一行,只搜不看)')
    ap.add_argument('--junk',default='',help='逗号分隔的路径前缀,其下文件不入检索索引(如模板碎片区)')
    a=ap.parse_args()
    recs=load(a.scan_dir,a.moves,a.deletes,a.roots); ch=build(recs)

    def stats(p):
        d=f=s=0
        for c in ch.get(p,[]):
            r=recs[c]
            if r.get('dir'):
                dd,ff,ss=stats(c); d+=1+dd; f+=ff+r.get('agg_files',0); s+=ss+(r.get('agg_size') or 0)
            else: f+=1; s+=r.get('size') or 0
        return d,f,s
    def media(p):
        e=Counter()
        def rec(q):
            for c in ch.get(q,[]):
                if recs[c].get('dir'): rec(c)
                else:
                    nm=recs[c]['name']; e[nm.rsplit('.',1)[-1].lower() if '.' in nm else '?']+=1
        rec(p); tot=sum(e.values()) or 1
        v=sum(e[x] for x in VID);au=sum(e[x] for x in AUD);d=sum(e[x] for x in DOC);i=sum(e[x] for x in IMG)
        top=max([('🎬视频',v),('🎧音频',au),('📄文档',d),('🖼图片',i)],key=lambda x:x[1])
        return top[0] if top[1]/tot>=0.5 else '📦混合'

    roots=sorted([p for p in recs if p.count('/')==1], key=lambda p:recs[p]['name'])
    EMOJI={'孩子':'👶','个人':'📖','技术':'🔧','影视':'🎬','书籍':'📚','存档':'🗄️'}
    out=[]
    # 概览表
    tot_d=tot_f=tot_s=0; rowsum=[]
    for r in roots:
        d,f,s=stats(r); tot_d+=d+1; tot_f+=f; tot_s+=s; rowsum.append((recs[r]['name'],d+1,f,s,recs[r].get('id')))
    out.append(f"---\ntype: moc\ntitle: {a.title}\ntags: [MOC, 云盘, 全盘索引]\n---\n")
    out.append(f"# ☁️ {a.title}\n")
    out.append(f"> {a.drive} · 全盘 **{tot_d:,} 目录 / {tot_f:,} 文件 / {human(tot_s)}** · 折叠标题浏览，点资源行 🔗 直达网盘")
    search_nav = " ▸ **搜单个文件** → `20_云盘地图/_全文检索/`（每区一份全文件清单，Ctrl+F/全局搜）" if a.search_dir else ""
    out.append(f"> 三样各司其职：**本文件**=浏览结构（清爽到资源级）；[[云盘馆藏.base|🃏 精选卡]]=15张策展卡；**_全文检索/**=搜任意单文件。{search_nav}")
    out.append("> 分类逻辑见 `20_云盘地图/` 各《深度分类方案》。\n")
    out.append("| 区 | 直达 | 目录 | 文件 | 体量 |")
    out.append("|---|---|---:|---:|---:|")
    for nm,d,f,s,fid in rowsum:
        lk=f"[🔗]({FOLDER_URL}{fid})" if fid else ""
        e=next((v for k,v in EMOJI.items() if k in nm),'📁')
        out.append(f"| {e} **{nm}** | {lk} | {d:,} | {f:,} | {human(s)} |")
    out.append("")

    def emit(path, level):
        subs=[c for c in ch.get(path,[]) if recs[c].get('dir')]
        files=[c for c in ch.get(path,[]) if not recs[c].get('dir')]
        nn=[c for c in subs if NN.match(recs[c]['name'])]
        res=[c for c in subs if not NN.match(recs[c]['name'])]
        # 本级资源表（非NN子目录 = 真实资源）
        rows=res[:]
        if rows or (files and level>=3):
            out.append(f"\n{'#'*min(level+1,6)} {recs[path]['name']}" if level>=2 else "")
            out.append("\n| 资源 | 类型 | 文件 | 大小 |")
            out.append("|---|---|---:|---:|")
            for c in rows:
                d,f,s=stats(c); fid=recs[c].get('id')
                nm=recs[c]['name'].replace('|','·').replace('[','〔').replace(']','〕')
                lk=f"[{nm} 🔗]({FOLDER_URL}{fid})" if fid else nm
                out.append(f"| {lk} | {media(c)} | {f:,} | {human(s)} |")
            if files and level>=3:
                fs=sum(recs[c].get('size') or 0 for c in files)
                out.append(f"| *（本级散文件 {len(files)}）* | | {len(files):,} | {human(fs)} |")
        elif level>=2:
            out.append(f"\n{'#'*min(level+1,6)} {recs[path]['name']}")
        # 递归结构夹（NN_）→ 子标题
        for c in nn: emit(c, level+1)

    for r in roots:
        e=next((v for k,v in EMOJI.items() if k in recs[r]['name']),'📁')
        fid=recs[r].get('id')
        out.append(f"\n# {e} {recs[r]['name']}" + (f" [🔗打开]({FOLDER_URL}{fid})" if fid else ""))
        emit(r, 1)
    open(a.out,'w').write("\n".join(x for x in out if x is not None)+"\n")
    print(f"OK {a.out} · {sum(1 for x in out if x)} 行 · {tot_d} 目录")

    if a.search_dir:
        os.makedirs(a.search_dir, exist_ok=True)
        junk=[j for j in a.junk.split(',') if j]
        NNp=re.compile(r'^\d{2}[_.]')
        def resource_of(p):
            segs=p.split('/')
            for i in range(2,len(segs)):
                if not NNp.match(segs[i]): return '/'.join(segs[:i+1])
            return '/'.join(segs[:-1])
        # 收集每区文件
        zfiles=defaultdict(list)
        for p,r in recs.items():
            if r.get('dir'): continue
            if any(p.startswith(j) for j in junk): continue
            zfiles[p.split('/')[1]].append(p)
        idx_total=0
        for zone in sorted(zfiles):
            files=sorted(zfiles[zone])
            idx_total+=len(files)
            by_res=defaultdict(list)
            for p in files: by_res[resource_of(p)].append(p)
            lines=[f"---\ntags: [云盘检索]\n区: {zone}\n---\n",
                   f"# 🔍 {zone} · 全文检索索引\n",
                   f"> 仅供 Ctrl+F / 全局搜索定位**单个文件**（共 {len(files):,} 个）；浏览结构请用 [[00_馆藏总览]]。**别在编辑模式久留（文件大）**。\n"]
            for res in sorted(by_res):
                rname=res.split('/',2)[-1] if res.count('/')>=2 else res
                lines.append(f"\n## {rname}")
                lines.append("\n| 文件 | 大小 |")
                lines.append("|---|---:|")
                for p in sorted(by_res[res]):
                    rel=p[len(res)+1:] if p.startswith(res+'/') else recs[p]['name']
                    rel=rel.replace('|','·')
                    lines.append(f"| {rel} | {human(recs[p].get('size'))} |")
            safe=zone.replace('/','_')
            open(os.path.join(a.search_dir, safe+'.md'),'w').write("\n".join(lines)+"\n")
        print(f"检索索引: {a.search_dir} · {len(zfiles)}个区文件 · {idx_total:,}行文件条目")

if __name__=='__main__': main()
