"""Read native template roles, or write measured paragraph spacing after export."""
import json,sys,hashlib
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from xml.etree import ElementTree as E
A='{http://schemas.openxmlformats.org/drawingml/2006/main}'
P='{http://schemas.openxmlformats.org/presentationml/2006/main}'
def read(path):
    roles={}
    with ZipFile(path) as z:
        size=E.fromstring(z.read('ppt/presentation.xml')).find(P+'sldSz')
        if (size.get('cx'),size.get('cy'))!=('12192000','6858000'):raise ValueError('Template must remain 1280×720')
        for name in z.namelist():
            if not name.startswith('ppt/slides/slide') or not name.endswith('.xml'):continue
            for sp in E.fromstring(z.read(name)).iter(P+'sp'):
                nv=sp.find('.//'+P+'cNvPr');key=nv.get('name','')
                if not key.startswith(('lesson.','question.')):continue
                if key in roles:raise ValueError('Duplicate template role: '+key)
                xf=sp.find(P+'spPr/'+A+'xfrm');off=xf.find(A+'off');ext=xf.find(A+'ext')
                d={k:int(v)/9525 for k,v in {**off.attrib,**ext.attrib}.items()}
                rp=sp.find('.//'+A+'defRPr')
                direct=sp.find('.//'+A+'rPr')
                if rp is not None or direct is not None:
                    def val(tag,attr):
                        for source in (direct,rp):
                            e=source.find(tag) if source is not None else None
                            if e is not None and e.get(attr) is not None:return e.get(attr)
                        return None
                    def attr(key,default):
                        for source in (direct,rp):
                            if source is not None and source.get(key) is not None:return source.get(key)
                        return default
                    d.update(font=val(A+'latin','typeface'),size=int(attr('sz','2400'))/75,bold=attr('b','0')=='1',color=val(A+'solidFill/'+A+'srgbClr','val'))
                    if d['color']:d['color']='#'+d['color']
                    ls=sp.find('.//'+A+'lnSpc/'+A+'spcPct')
                    pts=sp.find('.//'+A+'lnSpc/'+A+'spcPts')
                    d['lineSpacing']=int(ls.get('val'))/100000 if ls is not None else int(pts.get('val'))/(d['size']*75) if pts is not None else 1
                for field,xpath in [('fill',P+'spPr/'+A+'solidFill/'+A+'srgbClr'),('lineColor',P+'spPr/'+A+'ln/'+A+'solidFill/'+A+'srgbClr')]:
                    el=sp.find(xpath)
                    if el is not None:d[field]='#'+el.get('val')
                roles[key]=d
    return {'sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),'roles':roles}
def patch(path,ratios):
    with ZipFile(path) as z:files={n:z.read(n) for n in z.namelist()}
    for name,data in list(files.items()):
        if not name.startswith('ppt/slides/slide') or not name.endswith('.xml'):continue
        root=E.fromstring(data);page=name.rsplit('slide',1)[-1][:-4]
        for sp in root.iter(P+'sp'):
            nv=sp.find('.//'+P+'cNvPr');key=nv.get('name','');ratio=ratios.get(page+':'+key,ratios.get(key))
            if ratio is None:continue
            for par in sp.findall('./'+P+'txBody/'+A+'p'):
                pp=par.find(A+'pPr')
                if pp is None:pp=E.Element(A+'pPr');par.insert(0,pp)
                for old in pp.findall(A+'lnSpc'):pp.remove(old)
                # OOXML percent is based on the office font's natural line box,
                # not fontSize. Use explicit points to match Canvas height math.
                sizes=[int(e.get('sz')) for e in par.iter() if e.get('sz')]
                if not sizes:raise ValueError(f'{page}:{key}: missing explicit paragraph font size')
                if not isinstance(ratio,(float,int)) or ratio<1:raise ValueError('Invalid line spacing ratio')
                ls=E.Element(A+'lnSpc');E.SubElement(ls,A+'spcPts',val=str(round(max(sizes)*ratio)));pp.insert(0,ls)
        files[name]=E.tostring(root,encoding='utf-8',xml_declaration=True)
    tmp=Path(str(path)+'.tmp')
    with ZipFile(tmp,'w',ZIP_DEFLATED) as z:
        for n,data in files.items():z.writestr(n,data)
    tmp.replace(path)
if __name__=='__main__':
    if sys.argv[1]=='read':print(json.dumps(read(sys.argv[2])))
    elif sys.argv[1]=='patch':patch(sys.argv[2],json.loads(sys.argv[3]))
