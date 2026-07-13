#!/usr/bin/env python3
"""catalog 工作流：从全盘扫描 JSONL 生成「目录树标题 + 叶文件夹表格」的馆藏总览 + 全文检索索引。

通用、无私有数据硬编码。用法：
  gen_catalog.py --scan-dir DIR --out FILE [--moves f --deletes f --roots f --title T
                 --search-dir DIR --junk PREFIX --url-prefix URL --max-heading-depth N]

JSONL 每行：{"path","name","id","dir","size"[,"agg_files","agg_size"]}
约定：整理时的分类夹带 `NN_` 数字前缀（10_/20_…），真实资源用原名。
渲染：目录树每一级目录都成为标题，标题文本为从根目录开始的编号链 + 语义名 + 🔗直达；
直接含文件且无子目录的叶文件夹保持表格行，挂在父目录标题下，同一父目录下 >12 个叶文件夹压缩为 前2+计数+末1。
标题最多使用 H6；超过 H6 或 `--max-heading-depth` 的目录改用以 HTML 实体随层级缩进的加粗行。
点 🔗 落到文件所在文件夹；搜单个文件用 --search-dir 出的全文检索索引。

--url-prefix：阿里云盘网页版文件夹深链前缀。备份盘实测格式 = `https://www.alipan.com/drive/file/all/backup/<file_id>`
（`folder/<id>` 不工作会弹回首页）。不同盘位（资源盘/backup）末段不同，按实盘地址栏校准。
"""
import json, re, argparse, os
from collections import defaultdict, Counter
NN = re.compile(r'^\d{2}[_.]')
VID={'mp4','mkv','avi','flv','rmvb','mov','ts','wmv','m4v','mpg','vob'}
AUD={'mp3','wma','m4a','flac','wav','ape'}; DOC={'pdf','doc','docx','ppt','pptx','epub','txt','azw3','mobi','xls','xlsx'}; IMG={'jpg','jpeg','png','gif','bmp','webp'}
SERIES_CAP = 12  # 同一资源下叶文件夹超过此数则压缩

def human(n):
    n=n or 0
    for u in ['B','KB','MB','GB','TB']:
        if n<1024: return (f"{int(n)}B" if u=='B' else f"{n:.1f}{u}")
        n/=1024
    return f"{n:.1f}PB"

def esc(s): return s.replace('|','·').replace('[','〔').replace(']','〕')

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
        par=p.rsplit('/',1)[0] if '/' in p else ''
        ch[par].append(p)
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
    ap.add_argument('--url-prefix',default='https://www.alipan.com/drive/file/all/backup/',
                    help='网盘文件夹深链前缀(拼 file_id);备份盘实测 file/all/backup/')
    ap.add_argument('--max-heading-depth',type=int,default=None,
                    help='标题最大深度;超过此深度的目录改用缩进加粗行')
    a=ap.parse_args()
    U=a.url_prefix
    recs=load(a.scan_dir,a.moves,a.deletes,a.roots); ch=build(recs)

    def stats(p):
        d=f=s=0
        for c in ch.get(p,[]):
            r=recs[c]
            if r.get('dir'):
                dd,ff,ss=stats(c); d+=1+dd; f+=ff+r.get('agg_files',0); s+=ss+(r.get('agg_size') or 0)
            else: f+=1; s+=r.get('size') or 0
        return d,f,s
    def media(p, direct=False):
        e=Counter()
        def rec(q):
            for c in ch.get(q,[]):
                if recs[c].get('dir') and not direct: rec(c)
                elif not recs[c].get('dir'):
                    nm=recs[c]['name']; e[nm.rsplit('.',1)[-1].lower() if '.' in nm else '?']+=1
        rec(p); tot=sum(e.values()) or 1
        v=sum(e[x] for x in VID);au=sum(e[x] for x in AUD);d=sum(e[x] for x in DOC);i=sum(e[x] for x in IMG)
        top=max([('🎬视频',v),('🎧音频',au),('📄文档',d),('🖼图片',i)],key=lambda x:x[1])
        return top[0] if top[1]/tot>=0.5 else '📦混合'
    roots=sorted([p for p,r in recs.items() if r.get('dir') and
                  (p.rsplit('/',1)[0] if '/' in p else '') not in recs],
                 key=lambda p:recs[p]['name'])
    EMOJI={'孩子':'👶','个人':'📖','技术':'🔧','影视':'🎬','书籍':'📚','存档':'🗄️'}
    out=[]
    tot_d=tot_f=tot_s=0; rowsum=[]
    for r in roots:
        d,f,s=stats(r); tot_d+=d+1; tot_f+=f; tot_s+=s; rowsum.append((recs[r]['name'],d+1,f,s,recs[r].get('id')))
    out.append(f"---\ntype: moc\ntitle: {a.title}\ntags: [MOC, 云盘, 全盘索引]\n---\n")
    out.append(f"# ☁️ {a.title}\n")
    out.append(f"> {a.drive} · 全盘 **{tot_d:,} 目录 / {tot_f:,} 文件 / {human(tot_s)}** · 目录标题浏览，**表格保留叶文件夹**（真实文件所在层），点 🔗 直达该文件夹")
    search_nav = " ▸ **搜单个文件** → `20_云盘地图/_全文检索/`（每区一份全文件清单，Ctrl+F/全局搜）" if a.search_dir else ""
    out.append(f"> 三样各司其职：**本文件**=浏览+直达文件夹；[[云盘馆藏.base|🃏 精选卡]]=15张策展卡；**_全文检索/**=搜任意单文件。{search_nav}")
    out.append("> 分类逻辑见 `20_云盘地图/` 各《深度分类方案》。同一父目录下 >12 个叶文件夹已压缩为「前2+计数+末1」。\n")
    out.append("| 区 | 直达 | 目录 | 文件 | 体量 |")
    out.append("|---|---|---:|---:|---:|")
    for nm,d,f,s,fid in rowsum:
        lk=f"[🔗]({U}{fid})" if fid else ""
        e=next((v for k,v in EMOJI.items() if k in nm),'📁')
        out.append(f"| {e} **{nm}** | {lk} | {d:,} | {f:,} | {human(s)} |")
    out.append("")

    def rowfor(leaf, base, direct=False):
        fid=recs[leaf].get('id'); _,f,s=stats(leaf)
        if direct:
            files=[c for c in ch.get(leaf,[]) if not recs[c].get('dir')]
            f=len(files); s=sum(recs[c].get('size') or 0 for c in files)
        rel=esc(leaf[len(base)+1:] if leaf.startswith(base+'/') else recs[leaf]['name'])
        lk=f"[{rel} 🔗]({U}{fid})" if fid else rel
        return f"| {lk} | {media(leaf,direct)} | {f:,} | {human(s)} |"

    def title_text(path, root):
        root_parts=root.split('/'); path_parts=path.split('/')
        names=[recs[root]['name']]
        for i in range(len(root_parts),len(path_parts)):
            child='/'.join(path_parts[:i+1])
            names.append(recs.get(child,{}).get('name',path_parts[i]))
        chain=[]
        for name in names:
            m=NN.match(name); chain.append(m.group(0)[:2] if m else '-')
        m=NN.match(recs[path]['name'])
        semantic=recs[path]['name'][len(m.group(0)):] if m else recs[path]['name']
        return '.'.join(chain), semantic

    def title_line(path, root, level, emoji=None):
        chain,semantic=title_text(path,root)
        prefix=f"{emoji} " if emoji else ''
        fid=recs[path].get('id')
        lk=f" [🔗打开]({U}{fid})" if emoji and fid else (f" [🔗]({U}{fid})" if fid else '')
        text=f"{prefix}{chain} {semantic}"
        max_heading_level = min(6, a.max_heading_depth) if a.max_heading_depth is not None else 6
        if level<=max_heading_level:
            return f"{'#'*level} {text}{lk}"
        indent = max(0, level - max_heading_level - 1)
        return f"{'&nbsp;&nbsp;'*indent}**{text}**{lk}"

    def emit(path, level, root):
        subs=[c for c in ch.get(path,[]) if recs[c].get('dir')]
        direct_files=[c for c in ch.get(path,[]) if not recs[c].get('dir')]
        leaves=[c for c in subs if direct_files_for(c) and not dirs_for(c)]
        if direct_files or leaves:
            out.append("\n| 位置（🔗直达文件夹） | 类型 | 文件 | 大小 |")
            out.append("|---|---|---:|---:|")
            if direct_files: out.append(rowfor(path,path,True))
            if len(leaves)>SERIES_CAP:
                for leaf in leaves[:2]: out.append(rowfor(leaf,path))
                fid=recs[path].get('id'); rn=esc(recs[path]['name'])
                mid=f"[…{rn}（共{len(leaves)}个子文件夹）🔗]({U}{fid})" if fid else f"…{rn}（共{len(leaves)}个子文件夹）"
                out.append(f"| {mid} | | | |")
                out.append(rowfor(leaves[-1],path))
            else:
                for leaf in leaves: out.append(rowfor(leaf,path))
        for c in subs:
            if c in leaves: continue
            out.append("\n"+title_line(c,root,level+1))
            emit(c, level+1, root)

    def direct_files_for(node):
        return [c for c in ch.get(node,[]) if not recs[c].get('dir')]

    def dirs_for(node):
        return [c for c in ch.get(node,[]) if recs[c].get('dir')]

    for r in roots:
        nm=title_text(r,r)[1]
        e=next((v for k,v in EMOJI.items() if k in nm),'📁')
        out.append("\n"+title_line(r,r,1,e))
        emit(r, 1, r)
    open(a.out,'w').write("\n".join(x for x in out if x is not None)+"\n")
    print(f"OK {a.out} · {sum(1 for x in out if x)} 行 · {tot_d} 目录")

    if a.search_dir:
        os.makedirs(a.search_dir, exist_ok=True)
        junk=[j for j in a.junk.split(',') if j]
        def resource_of(p):
            segs=p.split('/')
            for i in range(2,len(segs)):
                if not NN.match(segs[i]): return '/'.join(segs[:i+1])
            return '/'.join(segs[:-1])
        zfiles=defaultdict(list)
        for p,r in recs.items():
            if r.get('dir'): continue
            if any(p.startswith(j) for j in junk): continue
            zfiles[p.split('/')[1]].append(p)
        idx_total=0
        for zone in sorted(zfiles):
            files=sorted(zfiles[zone]); idx_total+=len(files)
            by_res=defaultdict(list)
            for p in files: by_res[resource_of(p)].append(p)
            lines=[f"---\ntags: [云盘检索]\n区: {zone}\n---\n",
                   f"# 🔍 {zone} · 全文检索索引\n",
                   f"> 仅供 Ctrl+F / 全局搜索定位**单个文件**（共 {len(files):,} 个）；浏览/直达文件夹用 [[00_馆藏总览]]。**别在编辑模式久留（文件大）**。\n"]
            for res in sorted(by_res):
                rname=res.split('/',2)[-1] if res.count('/')>=2 else res
                rfid=recs.get(res,{}).get('id'); rlk=f" [🔗打开文件夹]({U}{rfid})" if rfid else ""
                lines.append(f"\n## {rname}{rlk}")
                lines.append("\n| 文件 | 大小 |")
                lines.append("|---|---:|")
                for p in sorted(by_res[res]):
                    rel=esc(p[len(res)+1:] if p.startswith(res+'/') else recs[p]['name'])
                    lines.append(f"| {rel} | {human(recs[p].get('size'))} |")
            open(os.path.join(a.search_dir, zone.replace('/','_')+'.md'),'w').write("\n".join(lines)+"\n")
        print(f"检索索引: {a.search_dir} · {len(zfiles)}个区文件 · {idx_total:,}行文件条目")

if __name__=='__main__': main()
