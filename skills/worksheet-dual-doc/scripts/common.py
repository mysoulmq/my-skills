"""Shared I/O primitives. Never infer correctness from a successful conversion."""
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from io import BytesIO
import json, os, subprocess, tempfile, zipfile, re
from lxml import etree
from docx.oxml.ns import qn
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
NS = {'w': W, 'r': R, 'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}

def digest(path): return sha256(Path(path).read_bytes()).hexdigest()
def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
def text(e):
    return ''.join(n.text or '' if n.tag==qn('w:t') else '\t' if n.tag==qn('w:tab') else '\n' for n in e.iter() if n.tag in (qn('w:t'),qn('w:tab'),qn('w:br'),qn('w:cr')) and n.getparent().tag==qn('w:r'))
def norm(s): return re.sub(r'\s+', '', s)
def image_hash(blob):
    im=Image.open(BytesIO(blob)).convert('RGBA')
    return sha256(str(im.size).encode()+im.tobytes()).hexdigest()
def image_ids(e): return e.xpath('.//a:blip/@r:embed')
def image_hashes(e, part): return [image_hash(part.related_parts[r].blob) for r in image_ids(e)]
def clone_block(e, source, dest):
    node=deepcopy(e)
    # A table may inherit all visible borders from a named source style.
    # Import that style and its base chain under private IDs to avoid template collisions.
    def import_style(style_id):
        new_id='WorksheetSource_'+style_id
        src_styles=source.document.styles.element
        dst_styles=dest.document.styles.element
        if dst_styles.xpath('./w:style[@w:styleId="'+new_id+'"]'):return new_id
        matches=src_styles.xpath('./w:style[@w:styleId="'+style_id+'"]')
        if not matches:raise ValueError('表格引用了缺失样式:'+style_id)
        copied=deepcopy(matches[0]);copied.set(qn('w:styleId'),new_id)
        for name in copied.findall(qn('w:name')):name.set(qn('w:val'),new_id)
        dst_styles.append(copied)
        for base in copied.findall(qn('w:basedOn')):base.set(qn('w:val'),import_style(base.get(qn('w:val'))))
        return new_id
    for st in node.xpath('.//w:tblStyle'):st.set(qn('w:val'),import_style(st.get(qn('w:val'))))
    for b in node.xpath('.//a:blip'):
        rid=b.get(qn('r:embed'))
        if rid:
            nr,_=dest.get_or_add_image(BytesIO(source.related_parts[rid].blob));b.set(qn('r:embed'),nr)
    for h in node.xpath('.//w:hyperlink'):
        # Flatten hyperlink wrapper, preserving displayed text and formatting.
        parent=h.getparent();idx=parent.index(h)
        for c in list(h):parent.insert(idx,c);idx+=1
        parent.remove(h)
    return node

def patch_text(e, start, end, replacement=''):
    """Edit visible character range without dropping neighboring pictures or run formatting."""
    atoms=[n for n in e.iter() if n.tag in (qn('w:t'),qn('w:tab'),qn('w:br'),qn('w:cr')) and n.getparent().tag==qn('w:r')]
    pos=0;inserted=False
    for n in atoms:
        val=n.text or '' if n.tag==qn('w:t') else '\t' if n.tag==qn('w:tab') else '\n'
        a,b=pos,pos+len(val);pos=b
        if b<=start or a>=end:continue
        new=val[:max(0,start-a)]+(replacement if not inserted else '')+val[min(len(val),end-a):]
        inserted=True
        if n.tag!=qn('w:t'):
            n.tag=qn('w:t')
        n.text=new;n.set('{http://www.w3.org/XML/1998/namespace}space','preserve')

def runtime_bin(name):
    dep=Path(os.sys.executable).parent.parent.parent
    for p in [dep/'bin/override'/name,dep/'bin/fallback'/name]:
        if p.exists():return str(p)
    import shutil
    p=shutil.which(name)
    if not p:raise RuntimeError(f'缺少运行工具 {name}；请加载 Codex workspace dependencies')
    return p

def office(files, out, fmt):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='worksheet-lo-',dir='/private/tmp' if Path('/private/tmp').exists() else None) as profile:
        env=dict(os.environ);env['TMPDIR']=tempfile.gettempdir()
        # Headless LibreOffice ships its own fontconfig; explicitly expose installed fonts.
        from fonts import resolve_fonts
        font_info=resolve_fonts();fonts=Path(font_info['directory'])
        # Add an actual source-label font only when files request it.
        needs_lisu=False
        for f in files:
            f=Path(f)
            if f.suffix.lower()=='.docx':
                with zipfile.ZipFile(f) as z:needs_lisu=needs_lisu or '隶书'.encode() in z.read('word/document.xml')
            elif f.suffix.lower()=='.doc':needs_lisu=needs_lisu or any(x in f.read_bytes() for x in ['隶书'.encode('utf-16-le'),'LiSu'.encode('utf-16-le'),b'LiSu'])
        source_dir=''
        if needs_lisu:
            from fonts import resolve_source_font
            source_dir=resolve_source_font()['directory']
        from xml.sax.saxutils import escape
        fc=Path(profile)/'fonts.conf'
        fc.write_text('<fontconfig><dir>'+escape(str(fonts))+'</dir>'+('<dir>'+escape(source_dir)+'</dir>' if source_dir else '')+'<alias><family>隶书</family><prefer><family>LiSu</family></prefer></alias><cachedir>'+escape(str(Path(profile)/'fontcache'))+'</cachedir><alias><family>宋体</family><prefer><family>SimSun</family></prefer></alias><alias><family>华文楷体</family><prefer><family>KaiTi</family></prefer></alias></fontconfig>')
        env['FONTCONFIG_FILE']=str(fc)
        cmd=[runtime_bin('soffice'),f'-env:UserInstallation={Path(profile).as_uri()}','--headless','--convert-to',fmt,'--outdir',str(out),*[str(Path(f).resolve()) for f in files]]
        r=subprocess.run(cmd,capture_output=True,text=True,timeout=180,env=env)
        suffix=fmt.split(':')[0]
        expected=[out/(Path(f).stem+'.'+suffix) for f in files]
        if r.returncode or not all(p.exists() and p.stat().st_size>0 for p in expected):
            raise RuntimeError(f'Office转换失败: {r.stdout}\n{r.stderr}')
        return expected

def prune(doc):
    """Remove unused images and source commentary/revision-bearing parts."""
    allowed=('styles','stylesWithEffects','settings','webSettings','fontTable','theme','numbering','header','footer','image')
    for rid,rel in list(doc.part.rels.items()):
        kind=rel.reltype.rsplit('/',1)[-1]
        if kind not in allowed or (kind=='image' and rid not in image_ids(doc._element)):
            doc.part.drop_rel(rid)
    for root in [doc._element,*[s.header._element for s in doc.sections],*[s.footer._element for s in doc.sections]]:
        for n in list(root.iter()):
            if n.tag in [qn('w:commentRangeStart'),qn('w:commentRangeEnd'),qn('w:commentReference'),qn('w:bookmarkStart'),qn('w:bookmarkEnd')]:
                if n.getparent() is not None:n.getparent().remove(n)
    doc.core_properties.comments='';doc.core_properties.author='';doc.core_properties.last_modified_by=''


def table_structure(e):
    """Semantic row/cell spans, independent of converter width rounding."""
    rows=[]
    for row in e.findall(qn('w:tr')):
        cells=[]
        for cell in row.findall(qn('w:tc')):
            spans=cell.xpath('./w:tcPr/w:gridSpan/@w:val')
            merges=cell.xpath('./w:tcPr/w:vMerge')
            merge=(merges[0].get(qn('w:val'),'continue') if merges else None)
            cells.append([int(spans[0]) if spans else 1,merge,norm(text(cell))])
        rows.append(cells)
    return rows
