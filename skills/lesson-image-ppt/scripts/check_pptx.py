"""Check source coverage/order in actual PPTX, not just the render plan."""
import argparse,json,re,xml.etree.ElementTree as ET
from pathlib import Path
from source_policy import display_units
from zipfile import ZipFile

NS={'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
normalize=lambda s:re.sub(r'\s+','',s)
def check(source,pptx):
    displayed=display_units(source)
    with ZipFile(pptx) as z:
        names=sorted([n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',n)],key=lambda n:int(re.search(r'(\d+)\.xml',n).group(1)))
        pages=[normalize(''.join(e.text or '' for e in ET.fromstring(z.read(n)).findall('.//a:t',NS))) for n in names]
    missing=[];mapping=[];order=[];cursor=(0,0)
    for u in source['units']:
        t=normalize(displayed[u['id']]);hits=[i+1 for i,p in enumerate(pages) if t in p]
        mapping.append({'id':u['id'],'pages':hits})
        if not hits:missing.append(u['id'])
        if u.get('kind','body')=='body':
            found=None
            for i in range(cursor[0],len(pages)):
                at=pages[i].find(t,cursor[1] if i==cursor[0] else 0)
                if at>=0:found=(i,at+len(t));break
            if found is None:order.append(u['id'])
            else:cursor=found
    traditional='踐' in ''.join(pages)
    return {'passed':not missing and not order and not traditional,'displayOmissions':source.get('displayOmissions',[]),'sourceUnits':len(source['units']),'slides':len(pages),'missing':missing,'outOfOrder':order,'traditionalJian':traditional,'mapping':mapping,'scope':'PPTX vs source transcription only; image accuracy and visual quality need independent review'}
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('source');ap.add_argument('pptx');ap.add_argument('--report',required=True);a=ap.parse_args()
    result=check(json.loads(Path(a.source).read_text()),a.pptx);Path(a.report).write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='mapping'},ensure_ascii=False));raise SystemExit(0 if result['passed'] else 1)
