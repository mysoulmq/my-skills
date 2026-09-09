#!/usr/bin/env python3
"""inspect / convert / verify / approve / config; no GUI required."""
from pathlib import Path
from datetime import datetime
import argparse,json,sys,shutil,re
from common import ROOT,write_json,office,digest
from inspect_input import inspect
from selection import select

def main():
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='command',required=True)
    p=sub.add_parser('inspect');p.add_argument('input');p.add_argument('--out')
    p=sub.add_parser('convert');p.add_argument('input');p.add_argument('--out',required=True);p.add_argument('--config');p.add_argument('--set',action='append',default=[])
    p=sub.add_parser('verify');p.add_argument('run')
    p=sub.add_parser('approve');p.add_argument('run');p.add_argument('--review',required=True)
    p=sub.add_parser('config');p.add_argument('--set',action='append',default=[]);p.add_argument('--save-defaults',action='store_true')
    args=ap.parse_args();default_path=ROOT/'assets/defaults.json';cfg=json.loads(default_path.read_text())
    if args.command in ['config','convert']:
        if getattr(args,'config',None):
            overrides=json.loads(Path(args.config).read_text())
            if set(overrides)-set(cfg):raise ValueError('未知配置项: '+str(set(overrides)-set(cfg)))
            cfg.update(overrides)
        for item in args.set:
            key,val=item.split('=',1)
            if key not in cfg:raise ValueError('未知配置项:'+key)
            cfg[key]=int(val) if key=='answer_space_lines' else val
        if not isinstance(cfg['answer_space_lines'],int) or not 0<=cfg['answer_space_lines']<=20:raise ValueError('答题留白必须是0至20行')
        if any(not isinstance(cfg[k],str) or '\n' in cfg[k] for k in cfg if k not in ['title','answer_space_lines']):raise ValueError('元数据必须是单行字符串')
    if args.command=='config':
        if args.save_defaults:write_json(default_path,cfg)
        print(json.dumps(cfg,ensure_ascii=False,indent=2));return
    if args.command=='inspect':
        result=select(inspect(args.input))
        if args.out:write_json(args.out,result)
        print(json.dumps(result,ensure_ascii=False,indent=2));return
    if args.command=='convert':
        from generate import generate,title_for
        model=select(inspect(args.input))
        if model['errors']:print(json.dumps(model,ensure_ascii=False,indent=2));sys.exit(2)
        base=Path(args.out);base.mkdir(parents=True,exist_ok=True)
        run=base/(Path(args.input).stem+'-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'));run.mkdir()
        (run/'internal').mkdir();(run/'candidates').mkdir()
        write_json(run/'input.json',model)
        write_json(run/'deletions.json',{'source':model['source'],'removed_questions':model['removed_questions'],'number_mapping':model['number_mapping']})
        manifests={}
        for v in ['题目版','答案版']:manifests[v]=generate(args.input,model,cfg,v,run/'internal'/f'{v}.docx')
        write_json(run/'manifest.json',{'source':model['source'],'source_sha256':model['source_sha256'],'config':cfg,'variants':manifests,'review_issues':model['review_issues']})
        office([run/'internal'/f'{v}.docx' for v in manifests],run/'candidates','doc:MS Word 97')
        from deletion_report import build
        build(model,run/'candidates/删除记录.pdf',title_for(model['title'],cfg))
        from verify_output import verify
        result=verify(run);print(json.dumps({'run':str(run.resolve()),**result},ensure_ascii=False,indent=2))
        if result['errors']:sys.exit(3)
    elif args.command=='verify':
        from verify_output import verify
        result=verify(args.run);print(json.dumps(result,ensure_ascii=False,indent=2))
        if result['errors']:sys.exit(3)
    elif args.command=='approve':
        run=Path(args.run);result=json.loads((run/'verification.json').read_text());review=json.loads(Path(args.review).read_text())
        if result['errors']:raise ValueError('自动检查未通过')
        for v,record in result['files'].items():
            if digest(run/'candidates'/f'{v}.doc')!=record['sha256']:raise ValueError('DOC审核后已变化')
            vr=review.get(v,{})
            if vr.get('sha256')!=record['sha256'] or vr.get('pages_checked')!=list(range(1,record['pages']+1)) or vr.get('issues')!=[]:raise ValueError('缺少与当前文件匹配的逐页审核')
        if review.get('content_review',{}).get('status')!='passed':raise ValueError('教研审核未通过')
        dest=run/'deliverables';dest.mkdir(exist_ok=True)
        from generate import title_for
        info=json.loads((run/'manifest.json').read_text());model=json.loads((run/'input.json').read_text())
        title=re.sub(r'\s+', ' ', title_for(model['title'],info['config'])).strip()
        title=re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', title).strip(' .')
        if not title:raise ValueError('无法生成可靠文件名')
        outputs={v:('（答案）' if v=='答案版' else '')+title+'.doc' for v in result['files']}
        if result.get('deletion_report'):
            record=result['deletion_report']
            if digest(run/'candidates/删除记录.pdf')!=record['sha256']:raise ValueError('删除PDF检查后已变化')
            if review.get('deletion_report',{}).get('sha256')!=record['sha256'] or review['deletion_report'].get('pages_checked')!=list(range(1,record['pages']+1)):raise ValueError('缺少删除PDF逐页审核')
            report_name=title+' 删除记录.pdf';shutil.copy2(run/'candidates/删除记录.pdf',dest/report_name);result['deletion_report']['filename']=report_name
        for v,name in outputs.items():shutil.copy2(run/'candidates'/f'{v}.doc',dest/name)
        result['deliverables']=outputs
        write_json(run/'review.json',review);result['status']='passed';write_json(run/'verification.json',result)
        print(dest.resolve())
if __name__=='__main__':
    try:main()
    except Exception as e:print(f'ERROR: {e}',file=sys.stderr);sys.exit(1)
