#!/usr/bin/env python3
"""catalog 工作流：从全盘扫描 JSONL 生成「目录树标题 + 叶文件夹表格」的馆藏总览 + 全文检索索引。

通用、无私有数据硬编码。用法：
  gen_catalog.py --scan-dir DIR --out FILE [--moves f --deletes f --roots f --title T
                 --search-dir DIR --junk PREFIX --url-prefix URL --catalog-link LINK
                 --cards-link LINK --classification-link LINK --max-heading-depth N]

JSONL 每行：{"path","name","id","dir","size"[,"agg_files","agg_size"]}
渲染：默认把全部目录作为标题，保证任意目录体系都不被隐藏；可用 `--heading-pattern` 提供用户自己的业务目录规则，
例如编号体系可传 `^\\d{2}[_.]`，把不匹配的内部素材目录折叠进表格。
标题文本直接使用当前实体目录名并可点击直达；
无编号的内部素材目录不进入大纲，按相对路径保持为表格行。同一业务目录下 >12 个素材文件夹压缩为 前2+计数+末1。
标题最多使用 H6；超过 H6 或 `--max-heading-depth` 时停留在最大标题级别，不输出 HTML 缩进实体。
点击课程标题或表格名称，直达对应文件夹；搜单个文件用 --search-dir 出的全文检索索引。

--url-prefix：阿里云盘网页版文件夹深链前缀。不同盘位的 URL 可能不同，必须由调用方显式传入
或通过 SOIA_ALIPAN_URL_PREFIX 提供，不在公共 skill 中写死用户盘位。
"""
import json, re, argparse, os
from datetime import date
from collections import defaultdict, Counter
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

OLD_HEADING_LINK = re.compile(
    r'^(?P<marks>#{1,6}\s+)(?P<emoji>\S+\s+)?(?P<title>\d{2}[_.].*?)\s+'
    r'\[🔗(?:打开)?\]\((?P<url>https?://[^)]+)\)\s*$',
    re.MULTILINE,
)
ROOT_HEADING = re.compile(
    r'^#\s+(?:\S+\s+)?\[(?P<name>[^\]]+)\]\([^)]+\)\s*$',
    re.MULTILINE,
)
GLOBAL_TOTALS = re.compile(
    r'全盘 \*\*(?P<dirs>[\d,]+) 目录 / (?P<files>[\d,]+) 文件 / (?P<size>[^*]+)\*\*'
)


def linkify_existing_headings(markdown):
    """把旧的“课程名 + 小图标链接”迁移为课程名本身可点击。"""
    def replace(match):
        emoji=match.group('emoji') or ''
        return f"{match.group('marks')}{emoji}[{match.group('title')}]({match.group('url')})"

    return OLD_HEADING_LINK.subn(replace, markdown)


def _partition_row(markdown, partition):
    pattern=re.compile(
        rf'^\|[^\n]*\*\*{re.escape(partition)}\*\*[^\n]*\|[ \t]*$',
        re.MULTILINE,
    )
    match=pattern.search(markdown)
    if not match:
        raise ValueError(f'未找到分区统计行：{partition}')
    cells=[cell.strip() for cell in match.group(0).split('|')[1:-1]]
    if len(cells)<5:
        raise ValueError(f'分区统计行列数不足：{partition}')
    try:
        dirs=int(cells[2].replace(',',''))
        files=int(cells[3].replace(',',''))
    except ValueError as error:
        raise ValueError(f'分区统计数字无法解析：{partition}') from error
    return match,dirs,files


def merge_partition_catalog(existing, generated, merge_date=None):
    """把单分区扫描结果合并进现有全盘总览，并同步总计与分区统计行。"""
    generated_roots=list(ROOT_HEADING.finditer(generated))
    if len(generated_roots)!=1:
        raise ValueError(f'增量目录必须且只能包含一个根分区，实际 {len(generated_roots)} 个')
    root_match=generated_roots[0]
    partition=root_match.group('name')
    new_row,new_dirs,new_files=_partition_row(generated,partition)
    old_row,old_dirs,old_files=_partition_row(existing,partition)

    old_root=re.search(
        rf'^#\s+(?:\S+\s+)?\[{re.escape(partition)}\]\([^)]+\)\s*$',
        existing,
        re.MULTILINE,
    )
    if not old_root:
        raise ValueError(f'现有总览未找到根分区标题：{partition}')
    next_root=ROOT_HEADING.search(existing,old_root.end())
    old_end=next_root.start() if next_root else len(existing)
    new_section=generated[root_match.start():].rstrip()+"\n\n"
    merged=existing[:old_root.start()]+new_section+existing[old_end:]

    merged=merged[:old_row.start()]+new_row.group(0)+merged[old_row.end():]
    # 历史版本可能让分区行后的空行进入表格；统一恢复连续的 Markdown 表格行。
    merged=re.sub(r'(?m)(^\|[^\n]*\|\n)(?:[ \t]*\n)+(?=\|)',r'\1',merged)
    totals=GLOBAL_TOTALS.search(merged)
    if not totals:
        raise ValueError('现有总览未找到全盘目录/文件总计')
    total_dirs=int(totals.group('dirs').replace(',',''))+new_dirs-old_dirs
    total_files=int(totals.group('files').replace(',',''))+new_files-old_files
    replacement=(
        f"全盘 **{total_dirs:,} 目录 / {total_files:,} 文件 / {totals.group('size')}**"
    )
    merged=merged[:totals.start()]+replacement+merged[totals.end():]

    stamp=merge_date or date.today().isoformat()
    note=(
        f"> 增量状态：`{partition}` 已于 {stamp} 全区重扫；目录数、文件数与分区内容已更新，"
        "其他分区沿用上次全盘扫描口径。"
    )
    if re.search(r'^> 增量状态：.*$',merged,re.MULTILINE):
        merged=re.sub(r'^> 增量状态：.*$',note,merged,count=1,flags=re.MULTILINE)
    else:
        anchor='> 分类逻辑见'
        line_end=merged.find('\n',merged.find(anchor))
        if line_end!=-1:
            merged=merged[:line_end+1]+note+'\n'+merged[line_end+1:]
    return merged,partition,new_dirs,new_files

def iter_scan_records(scan_dir):
    for fn in sorted(os.listdir(scan_dir)):
        if not fn.endswith('.jsonl'): continue
        with open(os.path.join(scan_dir,fn)) as source:
            for line in source:
                line=line.strip()
                if not line: continue
                try: r=json.loads(line)
                except: continue
                if not isinstance(r,dict) or 'path' not in r: continue
                p=r['path'].rstrip('/')
                if not r.get('name'): r['name']=p.rsplit('/',1)[-1]
                if r.get('name') and p.rsplit('/',1)[-1]!=r['name']:
                    p=p+'/'+r['name']; r={**r,'path':p}
                yield fn,p,r


def load(scan_dir, moves_f, del_f, roots_f):
    recs={}
    for fn,p,r in iter_scan_records(scan_dir):
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


def raw_stats_by_root(scan_dir, roots):
    """原始扫描统计保留同路径重名实体；目录树仍可按路径去重展示。"""
    result={root:[0,0,0] for root in roots}
    root_seen=set()
    for _,path,record in iter_scan_records(scan_dir):
        for root in roots:
            if path!=root and not path.startswith(root+'/'): continue
            if path==root: root_seen.add(root)
            if record.get('dir'):
                result[root][0]+=1
            else:
                result[root][1]+=1
                result[root][2]+=record.get('size') or 0
            break
    for root in roots:
        if root not in root_seen:
            result[root][0]+=1
    return result


def catalog_roots(recs, roots_f=None):
    """优先使用扫描时显式记录的根，避免 LIST_FAIL 造成的孤儿路径被误判为分区根。"""
    if roots_f and os.path.exists(roots_f):
        with open(roots_f) as source:
            declared=json.load(source)
        roots=[p.rstrip('/') for p in declared if p.rstrip('/') in recs and recs[p.rstrip('/')].get('dir')]
        if roots:
            return sorted(roots,key=lambda p:recs[p]['name'])
    return sorted(
        [p for p,r in recs.items() if r.get('dir') and
         (p.rsplit('/',1)[0] if '/' in p else '') not in recs],
        key=lambda p:recs[p]['name'],
    )

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
    ap.add_argument('--scan-dir'); ap.add_argument('--out',required=True)
    ap.add_argument('--linkify-existing',
                    help='只迁移现有总览的标题链接，不重扫数据；可与 --out 指向同一文件')
    ap.add_argument('--moves'); ap.add_argument('--deletes'); ap.add_argument('--roots')
    ap.add_argument('--merge-existing',help='把本次唯一根分区增量合并进现有全盘总览')
    ap.add_argument('--merge-date',default=date.today().isoformat(),help='增量状态日期 YYYY-MM-DD')
    ap.add_argument('--title',default='云盘馆藏总览'); ap.add_argument('--drive',default='云盘')
    ap.add_argument('--search-dir',help='额外输出:按区分的全文检索索引目录(每文件一行,只搜不看)')
    ap.add_argument('--junk',default='',help='逗号分隔的路径前缀,其下文件不入检索索引(如模板碎片区)')
    ap.add_argument('--url-prefix',default=os.environ.get('SOIA_ALIPAN_URL_PREFIX'),
                    help='网盘文件夹深链前缀(拼 file_id);也可用 SOIA_ALIPAN_URL_PREFIX')
    ap.add_argument('--catalog-link',default='',
                    help='可选：写入全文检索页的馆藏总览 wikilink 目标，不含 [[ ]]')
    ap.add_argument('--cards-link',default='',
                    help='可选：写入总览说明的精选卡 wikilink 目标，不含 [[ ]]')
    ap.add_argument('--classification-link',default='',
                    help='可选：写入总览说明的分类方案 wikilink 目标，不含 [[ ]]')
    ap.add_argument('--heading-pattern',default=os.environ.get('SOIA_ALIPAN_HEADING_PATTERN',r'.*'),
                    help='业务标题目录名正则；默认匹配全部目录，编号体系可传 ^\\d{2}[_.] 以折叠内部素材目录')
    ap.add_argument('--default-section-icon',default='📁',
                    help='根分区默认图标；公共默认不猜分区语义')
    ap.add_argument('--section-icons',default=os.environ.get('SOIA_ALIPAN_SECTION_ICONS',''),
                    help='可选：关键词到图标的 JSON 对象，如 {"学习":"📚"}')
    ap.add_argument('--max-heading-depth',type=int,default=None,
                    help='标题最大深度;更深的编号目录停留在该标题级别')
    a=ap.parse_args()
    if a.linkify_existing:
        markdown=open(a.linkify_existing).read()
        updated,count=linkify_existing_headings(markdown)
        open(a.out,'w').write(updated)
        print(f"OK {a.out} · {count} 个课程标题改为可点击")
        return
    if not a.scan_dir:
        ap.error('--scan-dir 与 --linkify-existing 至少提供一个')
    if not a.url_prefix:
        ap.error('--url-prefix 或 SOIA_ALIPAN_URL_PREFIX 必须提供，公共 skill 不猜用户盘位')
    try:
        heading_pattern=re.compile(a.heading_pattern)
    except re.error as error:
        ap.error(f'--heading-pattern 不是有效正则: {error}')
    try:
        section_icons=json.loads(a.section_icons) if a.section_icons else {}
    except json.JSONDecodeError as error:
        ap.error(f'--section-icons 不是有效 JSON: {error}')
    if not isinstance(section_icons,dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in section_icons.items()):
        ap.error('--section-icons 必须是字符串到字符串的 JSON 对象')
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
    roots=catalog_roots(recs,a.roots)
    raw_by_root=raw_stats_by_root(a.scan_dir,roots) if not a.moves and not a.deletes else {}
    out=[]
    tot_d=tot_f=tot_s=0; rowsum=[]
    for r in roots:
        if r in raw_by_root:
            d,f,s=raw_by_root[r]
        else:
            child_dirs,f,s=stats(r); d=child_dirs+1
        tot_d+=d; tot_f+=f; tot_s+=s; rowsum.append((recs[r]['name'],d,f,s,recs[r].get('id')))
    out.append(f"---\ntype: moc\ntitle: {a.title}\ntags: [MOC, 云盘, 全盘索引]\n---\n")
    out.append(f"# ☁️ {a.title}\n")
    out.append(f"> {a.drive} · 全盘 **{tot_d:,} 目录 / {tot_f:,} 文件 / {human(tot_s)}** · 业务目录标题浏览，**表格保留未匹配的素材文件夹**（真实文件所在层），点击资源标题或表格名称直达该文件夹")
    search_nav = "；已生成分区全文检索文件，可用 Ctrl+F/全局搜索" if a.search_dir else ""
    cards_nav = f"[[{a.cards_link}|精选卡]]" if a.cards_link else "精选卡（可选）"
    out.append(f"> 三样各司其职：**本文件**=浏览+直达文件夹；{cards_nav}=策展；全文检索=搜任意单文件{search_nav}。")
    classification = f"分类方案入口：[[{a.classification_link}]]。" if a.classification_link else "分类逻辑以用户确认的方案为准。"
    out.append(f"> {classification}同一业务目录下 >12 个素材文件夹已压缩为「前2+计数+末1」。\n")
    out.append("| 区 | 直达 | 目录 | 文件 | 体量 |")
    out.append("|---|---|---:|---:|---:|")
    for nm,d,f,s,fid in rowsum:
        lk=f"[🔗]({U}{fid})" if fid else ""
        e=next((v for k,v in section_icons.items() if k in nm),a.default_section_icon)
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

    def title_line(path, root, level, emoji=None):
        prefix=f"{emoji} " if emoji else ''
        fid=recs[path].get('id')
        name=recs[path]['name']
        text=f"{prefix}[{name}]({U}{fid})" if fid else f"{prefix}{name}"
        requested_depth = a.max_heading_depth if a.max_heading_depth is not None else 6
        max_heading_level = max(1, min(6, requested_depth))
        heading_level = min(level, max_heading_level)
        return f"{'#'*heading_level} {text}"

    def emit(path, level, root):
        direct_files=[c for c in ch.get(path,[]) if not recs[c].get('dir')]
        material_rows=[]
        numbered_children=[]

        def walk_unnumbered(node):
            for child in dirs_for(node):
                if heading_pattern.match(recs[child]['name']):
                    numbered_children.append(child)
                    continue
                if direct_files_for(child):
                    material_rows.append(child)
                walk_unnumbered(child)

        walk_unnumbered(path)
        collapse_material_tree = bool(material_rows) and not numbered_children
        if direct_files or material_rows:
            out.append("\n| 位置（🔗直达文件夹） | 类型 | 文件 | 大小 |")
            out.append("|---|---|---:|---:|")
            if collapse_material_tree:
                out.append(rowfor(path,path,False))
            elif direct_files:
                out.append(rowfor(path,path,True))
            if not collapse_material_tree and len(material_rows)>SERIES_CAP:
                for leaf in material_rows[:2]: out.append(rowfor(leaf,path,True))
                fid=recs[path].get('id'); rn=esc(recs[path]['name'])
                mid=f"[…{rn}（共{len(material_rows)}个素材文件夹）🔗]({U}{fid})" if fid else f"…{rn}（共{len(material_rows)}个素材文件夹）"
                out.append(f"| {mid} | | | |")
                out.append(rowfor(material_rows[-1],path,True))
            elif not collapse_material_tree:
                for leaf in material_rows: out.append(rowfor(leaf,path,True))
        for c in numbered_children:
            out.append("\n"+title_line(c,root,level+1))
            emit(c, level+1, root)

    def direct_files_for(node):
        return [c for c in ch.get(node,[]) if not recs[c].get('dir')]

    def dirs_for(node):
        return [c for c in ch.get(node,[]) if recs[c].get('dir')]

    for r in roots:
        nm=recs[r]['name']
        e=next((v for k,v in section_icons.items() if k in nm),a.default_section_icon)
        out.append("\n"+title_line(r,r,1,e))
        emit(r, 1, r)
    markdown="\n".join(x for x in out if x is not None)+"\n"
    merged_partition=None
    if a.merge_existing:
        existing=open(a.merge_existing).read()
        markdown,merged_partition,_,_=merge_partition_catalog(existing,markdown,a.merge_date)
    with open(a.out,'w') as target:
        target.write(markdown)
    suffix=f" · 增量合并 {merged_partition}" if merged_partition else ""
    print(f"OK {a.out} · {sum(1 for x in out if x)} 行 · {tot_d} 目录{suffix}")

    if a.search_dir:
        os.makedirs(a.search_dir, exist_ok=True)
        junk=[j for j in a.junk.split(',') if j]
        def root_of(p):
            matches=[root for root in roots if p==root or p.startswith(root+'/')]
            return max(matches,key=len) if matches else None

        def resource_of(p, root):
            relative=p[len(root):].lstrip('/')
            parts=[part for part in relative.split('/') if part]
            current=root
            # 最后一段是文件名；只检查目录，避免把文件误判成资源根。
            for part in parts[:-1]:
                current=f"{current}/{part}"
                if not heading_pattern.match(part): return current
            return p.rsplit('/',1)[0]
        zfiles=defaultdict(list)
        for p,r in recs.items():
            if r.get('dir'): continue
            if any(p.startswith(j) for j in junk): continue
            root=root_of(p)
            if root is None:
                continue
            zfiles[root].append(p)
        idx_total=0
        for zone_root in sorted(zfiles,key=lambda root:recs[root]['name']):
            zone=recs[zone_root]['name']
            files=sorted(zfiles[zone_root]); idx_total+=len(files)
            by_res=defaultdict(list)
            for p in files: by_res[resource_of(p,zone_root)].append(p)
            catalog_ref=f"[[{a.catalog_link}]]" if a.catalog_link else "本次馆藏总览产物"
            lines=[f"---\ntags: [云盘检索]\n区: {zone}\n---\n",
                   f"# 🔍 {zone} · 全文检索索引\n",
                   f"> 仅供 Ctrl+F / 全局搜索定位**单个文件**（共 {len(files):,} 个）；浏览/直达文件夹用 {catalog_ref}。**别在编辑模式久留（文件大）**。\n"]
            for res in sorted(by_res):
                rname=res[len(zone_root):].lstrip('/') or zone
                rfid=recs.get(res,{}).get('id'); rlk=f" [🔗打开文件夹]({U}{rfid})" if rfid else ""
                lines.append(f"\n## {rname}{rlk}")
                lines.append("\n| 文件 | 大小 |")
                lines.append("|---|---:|")
                for p in sorted(by_res[res]):
                    rel=esc(p[len(res)+1:] if p.startswith(res+'/') else recs[p]['name'])
                    lines.append(f"| {rel} | {human(recs[p].get('size'))} |")
            with open(os.path.join(a.search_dir, zone.replace('/','_')+'.md'),'w') as target:
                target.write("\n".join(lines)+"\n")
        print(f"检索索引: {a.search_dir} · {len(zfiles)}个区文件 · {idx_total:,}行文件条目")

if __name__=='__main__': main()
