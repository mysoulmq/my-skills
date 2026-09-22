import fs from 'node:fs/promises';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {pathToFileURL} from 'node:url';
import {FONT,C,text,line,node,connect,linesOf,richTextRows} from './graphics.mjs';
const {Presentation,PresentationFile}=await import(pathToFileURL(path.join(process.env.LESSON_NODE_MODULES,'@oai/artifact-tool/dist/artifact_tool.mjs')));
const [sourcePath,deckPath,outPath]=process.argv.slice(2);
if(!outPath)throw Error('Usage: node render.mjs source.json deck.json output-directory');
const out=path.resolve(outPath);await fs.mkdir(out,{recursive:true});
const source=JSON.parse(await fs.readFile(sourcePath,'utf8'));
const deck=JSON.parse(await fs.readFile(deckPath,'utf8'));
try { execFileSync(process.env.LESSON_PYTHON||'python3', [fileURLToPath(new URL('./check_plan.py',import.meta.url)),sourcePath,deckPath,'--report',path.join(out,'plan-check.json')],{encoding:'utf8'}); }
catch(e){throw Error(`Teaching plan check failed before rendering: ${e.stdout||e.message}`);}

const hasMarks=o=>o&&typeof o==='object'&&(Array.isArray(o.marks)||Object.values(o).some(hasMarks));
if(hasMarks(deck)&&deck._highlightPlan?.version!==1)throw Error('Compile marks with prepare_marks.py before rendering');
const units=new Map(source.units.map(u=>[u.id,u]));
if(units.size!==source.units.length)throw Error('Duplicate source IDs');
const norm=s=>String(s).replace(/\s/g,'');
const displayed=new Map(source.units.map(u=>[u.id,u.text])),omitted=new Set();
for(const rule of source.displayOmissions??[]){
 const {id,prefix,reason,authorization}=rule,raw=displayed.get(id);
 if(!raw||omitted.has(id)||typeof prefix!=='string'||!/^([①-⑳]|[0-9]{1,2}[、.．])$/.test(prefix)||!String(reason??'').trim()||!String(authorization??'').trim()||!raw.startsWith(prefix)||!raw.slice(prefix.length).trim())throw Error(`Invalid authorized numbering omission: ${id}`);
 omitted.add(id);displayed.set(id,raw.slice(prefix.length));
}

const allSource=source.units.map(u=>norm(u.text)).join('');
const layoutReview=[];const usage=[],summaryEvidence=[],revealPlan={slides:[]};const p=Presentation.create({slideSize:{width:1280,height:720}});
function resolve(o){
 if(typeof o==='string')o={ref:o};
 if(o.ref){const u=units.get(o.ref);if(!u)throw Error(`Unknown ref ${o.ref}`);const t=o.text??displayed.get(o.ref);if(norm(t)!==norm(displayed.get(o.ref)))throw Error(`Text override changes source ${o.ref}`);return {...o,text:t};}
 if(o.text && !allSource.includes(norm(o.text)))throw Error(`Diagram label not in source: ${o.text}`);
 return o;
}
function put(s,input,x,y,w,h,opts={}){const o=resolve(input);if(o.ref)usage.push({id:o.ref,slide:s._lessonNumber});return text(s,o.text,x,y,w,h,{...opts,...o,sourceId:o.ref||''});}
function measure(o,w,size=32){return Math.ceil(richTextRows(o.text,w,{...o,size}).length*size*(o.lineSpacing??1.12)+6);}
function height(o,w,size=32){return measure(resolve(o),w,size);}
function paraBlock(s,items,y,{x=56,w=1168,size=32,gap=15}={}){
 for(const input of items){const o=resolve(input);const sz=o.size||size;if(sz<26)throw Error('Body font below 26px; review source grouping and layout');const inset=o.bullet?64:(o.indent||0);const h=height(o,w-inset,sz);if(y+h>650)throw Error(`Slide ${s._lessonNumber}: body overflow; split slide (${o.ref||o.text})`);
 if(o.bullet)text(s,'•',x+28,y,28,sz*1.5,{size:sz,color:C.accent,sourceId:o.ref?`${o.ref}--bullet`:''});
 put(s,o,x+inset,y,w-inset,h,{size:sz});y+=h+(o.gap??gap);
 }return y;
}
function branches(s,b,y){
 const rw=b.rootWidth||230,bx=rw+132,bw=1224-bx,size=b.size||32,gap=b.gap??22;
 if(size<26||b.items.some(o=>(resolve(o).size||size)<26))throw Error('Branch body font below 26px; review source grouping and layout');
 const hs=b.items.map(o=>height(o,bw,resolve(o).size||size));const needed=hs.reduce((a,v)=>a+v,0)+gap*(hs.length-1);
 if(y+needed>650)throw Error(`Slide ${s._lessonNumber}: branches overflow (${needed}px); split slide`);
 const root=resolve(b.root);if(/^[①②③④⑤⑥⑦⑧⑨⑩\d\s、.：:]+$/.test(root.text))throw Error('Meaningless number-only node');
 const rh=Math.max(86,height({...root,bold:true},rw-30,b.rootSize||30)+24);
 if(rh>needed+35)throw Error('Root too tall for branch group');
 const r=node(s,root.text,56,y+(needed-rh)/2,rw,rh,{size:b.rootSize||30});if(root.ref)usage.push({id:root.ref,slide:s._lessonNumber});
 let yy=y;
 for(let i=0;i<b.items.length;i++){const o=resolve(b.items[i]);const l=put(s,o,bx,yy,bw,hs[i],{size:o.size||size});connect(s,r,l);yy+=hs[i]+gap;}
 return y+needed+26;
}
function table(s,b,y){
 const rows=b.rows.map(row=>row.map(resolve)),widths=b.widths||rows[0].map(()=>1168/rows[0].length),size=b.size||27;
 if(size<24)throw Error('Table font below 24px; review column widths and row grouping');
 if(Math.abs(widths.reduce((a,v)=>a+v,0)-1168)>1)throw Error('Table widths must sum to 1168');
 const heights=rows.map((row,i)=>Math.max(...row.map((o,c)=>height({...o,bold:i===0},widths[c]-20,size)))+14);
 if(y+heights.reduce((a,v)=>a+v,0)>650)throw Error(`Slide ${s._lessonNumber}: table overflow; split by rows`);
 const vals=rows.map((row,i)=>row.map((o,c)=>{if(o.ref)usage.push({id:o.ref,slide:s._lessonNumber});return linesOf(o.text,widths[c]-20,size,i===0,o.emphasis||[]).join('\n');}));
 const t=s.tables.add({rows:rows.length,columns:rows[0].length,left:56,top:y,width:1168,height:heights.reduce((a,v)=>a+v,0),columnWidths:widths,values:vals});
 heights.forEach((h,i)=>t.rows[i].height=h);t.borders.assign({fill:C.line,width:1,style:'solid'});
 for(let r=0;r<rows.length;r++)for(let c=0;c<rows[0].length;c++){const cell=t.getCell(r,c);cell.fill=r===0?C.accent:c===0?C.light:'#FFFFFF';cell.text.style={typeface:FONT,fontSize:size,bold:r===0,color:r===0?'#FFFFFF':C.ink,alignment:r===0||c===0?'center':'left',verticalAlignment:'middle',autoFit:'none',lineSpacing:1.05,insets:{left:10,right:10,top:6,bottom:6}};cell.value=richTextRows(rows[r][c].text,widths[c]-20,{...rows[r][c],size,bold:r===0||rows[r][c].bold||false,color:r===0?'#FFFFFF':C.ink});}
 return y+heights.reduce((a,v)=>a+v,0)+26;
}
function mapLabel(input,separator='：'){
 if(input?.segments){
  const segmentInputs=input.label?[input.label,...input.segments]:input.segments;
  const texts=segmentInputs.map(seg=>{const u=units.get(seg.ref);if(!u||!norm(u.text).includes(norm(seg.quote)))throw Error(`Unsupported map excerpt: ${seg.ref}: ${seg.quote}`);summaryEvidence.push({ref:seg.ref,quote:seg.quote});return seg.quote;});
  const textValue=input.label?texts[0]+(input.separator??separator)+texts.slice(1).join(input.join??'；'):texts.join(input.join??'；');
  return {...input,text:textValue};
 }
 const o=resolve(input);if(o.ref)summaryEvidence.push({ref:o.ref,quote:o.text});return o;
}
function mapText(s,input,x,y,w,h,opt={}){const o=mapLabel(input);return text(s,o.text,x,y,w,h,{...opt,...o});}
function brace(s,x,y,h,color,name){s.shapes.add({geometry:'leftBrace',name,position:{left:x,top:y,width:18,height:h},fill:'none',line:{fill:color,width:2.5}});}
function referenceKnowledgeMap(s,d){
 s.background.fill='#FFFFFF';
 const black='#000000',cfg=d.mapLayout??{},compact=d.groups.length===1&&d.groups[0].topics.length===1;
 const frameWidth=cfg.frameWidth??230,topicWidth=cfg.topicWidth??184;
 const frameLineColor=cfg.frameLineColor??'#ED7D31',topicLineColor=cfg.topicLineColor??'#4472C4',leafLineColor=cfg.leafLineColor??'#4472C4';
 for(const color of [frameLineColor,topicLineColor,leafLineColor])if(!/^#[0-9a-f]{6}$/i.test(color))throw Error('Map line colors must be #RRGGBB');
 if(cfg.headingSize!==undefined&&(!Number.isFinite(cfg.headingSize)||cfg.headingSize<21||cfg.headingSize>36))throw Error('Map headingSize must be within 21–36px');
 if(!Number.isFinite(frameWidth)||frameWidth<180||!Number.isFinite(topicWidth)||topicWidth<160)throw Error('Map frame/topic columns must be at least 180/160px');
 const topicX=154+frameWidth+58,leafX=compact?362:topicX+topicWidth+24,leafWidth=1250-leafX;
 if(leafWidth<400)throw Error('Map column widths must leave at least 400px for full memory clues');
 const lineSpacing=cfg.lineSpacing??1.04,groupGap=cfg.groupGap??18,topicGap=cfg.topicGap??10,leafGap=cfg.leafGap??3;
 for(const [key,v] of Object.entries({lineSpacing,groupGap,topicGap,leafGap}))if(!Number.isFinite(v)||v<0)throw Error(`Invalid mapLayout.${key}`);
 if(lineSpacing<1)throw Error('Map line spacing below 1 risks clipping');
 const minSize=cfg.minSize??22,maxSize=d.size??26;
 if(minSize<21||minSize>maxSize||maxSize>36)throw Error('Map font range must be within 21–36px');
 const prepared=d.groups.map(g=>({label:mapLabel(g.title),topics:g.topics.map(t=>({label:mapLabel(t.title),leaves:t.leaves.map(l=>{
  if(!l.label?.ref||!l.label?.quote)throw Error('Each knowledge-map leaf needs label:{ref,quote} naming its knowledge point');
  const o={...mapLabel(l,'——'),bold:l.bold??true,italicAfter:l.italicAfter??(l.separator??'——'),lineSpacing};
  if(o.size)throw Error('Set map font range on the slide, not individual leaves');
  return o;
 })}))}));
 const available=compact?548:684;let groups,total,size,headingSize;
 for(size=maxSize;size>=minSize;size--){
  headingSize=cfg.headingSize??Math.max(size,24);
  groups=prepared.map(g=>{const topics=g.topics.map(t=>{
   const leaves=t.leaves.map(o=>({o,h:measure(o,leafWidth,size)}));
   const h=Math.max(measure({...t.label,bold:true,lineSpacing},topicWidth,headingSize),leaves.reduce((v,l)=>v+l.h,0)+leafGap*Math.max(0,leaves.length-1));
   return {...t,leaves,h};
  });return {...g,topics,h:Math.max(measure({...g.label,bold:true,lineSpacing},frameWidth-24,headingSize)+24,topics.reduce((v,t)=>v+t.h,0)+topicGap*Math.max(0,topics.length-1))};});
  total=groups.reduce((v,g)=>v+g.h,0)+groupGap*Math.max(0,groups.length-1);
  if(total<=available)break;
 }
 if(total>available)throw Error(`Slide ${s._lessonNumber}: whole-lesson map needs ${total}px at ${minSize}px; shorten evidence-backed memory clues or tune mapLayout; do not replace it with separate topic maps`);
 const top=(compact?130:12)+(available-total)/2;
 layoutReview.push({slide:s._lessonNumber,type:'knowledge-map',groups:groups.length,topics:groups.reduce((n,g)=>n+g.topics.length,0),leaves:groups.reduce((n,g)=>n+g.topics.reduce((m,t)=>m+t.leaves.length,0),0),size,headingSize,lineSpacing,total,available,top,leafX,leafWidth,frameWidth,topicWidth,frameLineColor,topicLineColor,leafLineColor,groupGap,topicGap,leafGap});
 const box=(o,x,y,w,h,name,fontSize=headingSize)=>node(s,o.text,x,y,w,h,{...o,size:fontSize,bold:true,color:black,fill:'none',stroke:black,pad:12,lineSpacing,sourceId:name});
 if(compact){
  put(s,deck.lesson,36,20,1208,44,{size:30,bold:true,color:black});
  const g=groups[0],t=g.topics[0];text(s,g.label.text,36,74,1208,44,{...g.label,size:24,color:black,sourceId:'map-frame-1'});
  const rh=measure({...t.label,bold:true,lineSpacing},206,headingSize)+24;
  box(t.label,56,top+(total-rh)/2,230,rh,'map-topic-1-1');brace(s,324,top,total,leafLineColor,'map-brace-leaves-1-1');
  let y=top;const steps=[];
  for(const [li,l] of t.leaves.entries()){const name=`map-leaf-1-1-${li+1}`;text(s,l.o.text,leafX,y,leafWidth,l.h,{...l.o,size,color:black,sourceId:name});steps.push([name]);y+=l.h+leafGap;}
  if(d.reveal!==false)revealPlan.slides.push({slide:s._lessonNumber,steps});return;
 }
 const root=mapLabel(d.root||deck.lesson),vertical={...root,text:Array.from(root.text.replace(/\s/g,'')).join('\n')};
 const rootSize=26,rootHeight=measure({...vertical,bold:true,lineSpacing},32,rootSize)+24;
 if(rootHeight>684)throw Error('Vertical lesson title too tall; use a source-backed shorter title label');
 box(vertical,20,12+(684-rootHeight)/2,56,rootHeight,'map-root',rootSize);
 if(root.ref)usage.push({id:root.ref,slide:s._lessonNumber});brace(s,108,top,total,frameLineColor,'map-brace-frames');
 const steps=[];let gy=top;
 for(const [gi,g] of groups.entries()){
  const fh=measure({...g.label,bold:true,lineSpacing},frameWidth-24,headingSize)+24;
  box(g.label,154,gy+(g.h-fh)/2,frameWidth,fh,`map-frame-${gi+1}`);
  brace(s,topicX-28,gy,g.h,topicLineColor,`map-brace-topics-${gi+1}`);
  const topicsTotal=g.topics.reduce((v,t)=>v+t.h,0)+topicGap*(g.topics.length-1);let ty=gy+(g.h-topicsTotal)/2;
  for(const [ti,t] of g.topics.entries()){
   const th=measure({...t.label,bold:true,lineSpacing},topicWidth,headingSize);
   text(s,t.label.text,topicX,ty+(t.h-th)/2,topicWidth,th,{...t.label,size:headingSize,lineSpacing,bold:true,color:black,sourceId:`map-topic-${gi+1}-${ti+1}`});
   brace(s,leafX-24,ty,t.h,leafLineColor,`map-brace-leaves-${gi+1}-${ti+1}`);
   steps.push([`map-topic-${gi+1}-${ti+1}`,`map-brace-leaves-${gi+1}-${ti+1}`]);let ly=ty;
   for(const [li,l] of t.leaves.entries()){const name=`map-leaf-${gi+1}-${ti+1}-${li+1}`;text(s,l.o.text,leafX,ly,leafWidth,l.h,{...l.o,size,color:black,sourceId:name});steps.push([name]);ly+=l.h+leafGap;}
   ty+=t.h+topicGap;
  }gy+=g.h+groupGap;
 }
 if(d.reveal!==false)revealPlan.slides.push({slide:s._lessonNumber,steps});
}
function knowledgeMap(s,d){
 if((d.mapStyle||'reference')==='reference')return referenceKnowledgeMap(s,d);
 if(d.mapStyle!=='teal')throw Error('Unknown mapStyle');
 const size=d.size||26;if(size<26)throw Error('Knowledge map too small; split by frame/topic');
 put(s,deck.lesson,36,22,1208,52,{size:36,bold:true,color:C.navy});
 const groupGap=24,topicGap=18,leafGap=12;
 const compact=d.groups.length===1&&d.groups[0].topics.length===1;const leafWidth=compact?862:464;
 const groups=d.groups.map(g=>{const topics=g.topics.map(t=>{
  const leaves=t.leaves.map(l=>{if(!l.label?.ref||!l.label?.quote)throw Error('Each knowledge-map leaf needs label:{ref,quote} naming its knowledge point');const o=mapLabel(l);if(o.size&&o.size!==size)throw Error('Set knowledge-map size on the slide, not individual leaves');const h=measure(o,leafWidth,size);return {o,h};});
  const label=mapLabel(t.title),lh=measure({...label,bold:true},218,27);
  return {label,leaves,h:Math.max(lh,leaves.reduce((a,l)=>a+l.h,0)+leafGap*(leaves.length-1))};
 });const label=mapLabel(g.title);return {label,topics,h:Math.max(measure({...label,bold:true},190,27)+24,topics.reduce((a,t)=>a+t.h,0)+topicGap*(topics.length-1))};});
 const total=groups.reduce((a,g)=>a+g.h,0)+groupGap*(groups.length-1);
 if(total>550)throw Error(`Knowledge map too tall (${total}); split groups/topics across map pages, never drop detail or shrink below 26`);
 const top=compact?136+(508-total)/2:94+(550-total)/2;
 if(compact){
  const g=groups[0],t=g.topics[0];if(total>508)throw Error('Topic map too tall; shorten excerpt or split meaningful subgroups');
  text(s,g.label.text,36,78,1208,50,{size:24,color:C.muted,sourceId:'map-frame-1'});
  const rh=measure({...t.label,bold:true},200,29)+24;node(s,t.label.text,56,top+(total-rh)/2,230,rh,{size:29,sourceId:'map-topic-1-1'});brace(s,324,top,total,'#21A3AD','map-brace-leaves-1-1');
  let y=top;const steps=[];for(const [li,l] of t.leaves.entries()){const name=`map-leaf-1-1-${li+1}`;text(s,l.o.text,362,y,862,l.h,{size,...l.o,sourceId:name});steps.push([name]);y+=l.h+leafGap;}if(d.reveal!==false)revealPlan.slides.push({slide:s._lessonNumber,steps});return;
 }
 const root=mapLabel(d.root),rh=measure({...root,bold:true},134,28)+24;
 node(s,root.text,28,top+(total-rh)/2,164,rh,{size:28,sourceId:'map-root'});brace(s,204,top,total,'#E58A35','map-brace-frames');
 let gy=top;const steps=[];
 for(const [gi,g] of groups.entries()){const fh=measure({...g.label,bold:true},190,27)+24;node(s,g.label.text,226,gy+(g.h-fh)/2,210,fh,{size:27,focus:g.label.focus||[],contrast:g.label.contrast||[],sourceId:`map-frame-${gi+1}`});brace(s,452,gy,g.h,'#537CAC',`map-brace-topics-${gi+1}`);let ty=gy;
 for(const [ti,t] of g.topics.entries()){const th=measure({...t.label,bold:true},218,27);text(s,t.label.text,480,ty+(t.h-th)/2,218,th,{size:27,bold:true,color:C.navy,focus:t.label.focus||[],contrast:t.label.contrast||[],sourceId:`map-topic-${gi+1}-${ti+1}`});brace(s,726,ty,t.h,'#21A3AD',`map-brace-leaves-${gi+1}-${ti+1}`);steps.push([`map-topic-${gi+1}-${ti+1}`,`map-brace-leaves-${gi+1}-${ti+1}`]);let ly=ty;
 for(const [li,l] of t.leaves.entries()){const name=`map-leaf-${gi+1}-${ti+1}-${li+1}`;text(s,l.o.text,760,ly,464,l.h,{size,...l.o,sourceId:name});steps.push([name]);ly+=l.h+leafGap;}ty+=t.h+topicGap;}
 gy+=g.h+groupGap;}
 if(d.reveal!==false)revealPlan.slides.push({slide:s._lessonNumber,steps});
}
for(let i=0;i<deck.slides.length;i++){
 const d=deck.slides[i],s=p.slides.add();s._lessonNumber=i+1;s.background.fill=C.bg;
 if(d.type==='knowledge-map'){knowledgeMap(s,d);}else if(d.type==='overview'){
 put(s,deck.lesson,56,83,1168,75,{size:50,bold:true,color:C.navy});
 if(d.kicker)put(s,d.kicker,56,26,1100,38,{size:22,color:C.muted});
 const groups=d.groups;if(groups.length<1||groups.length>3)throw Error('Overview supports 1-3 frame groups; split if needed');
 const root=resolve(d.root);const r=node(s,root.text,56,361,250,100,{size:30});if(root.ref)usage.push({id:root.ref,slide:i+1});
 const gh=450/groups.length;
 groups.forEach((g,j)=>{const top=205+j*gh,mid=top+gh/2,fr=resolve(g.title),fh=height({...fr,bold:true},292,28)+24;
 const n=node(s,fr.text,371,mid-fh/2,322,fh,{size:28});if(fr.ref)usage.push({id:fr.ref,slide:i+1});connect(s,r,n);
 const step=gh/g.items.length;if(step<55)throw Error('Too many overview leaves');
 g.items.forEach((o,k)=>{const h=height(o,460,28);if(h>step)throw Error('Overview leaf too tall');const l=put(s,o,764,top+k*step+(step-h)/2,460,h,{size:28,bold:true,color:C.navy});connect(s,n,l);});
 });
 }else{
 put(s,deck.lesson,56,26,554,37,{size:22,color:C.muted});
 if(d.frame)put(s,d.frame,580,26,644,37,{size:22,color:C.muted,align:'right'});
 const title=resolve(d.title),titleSize=d.titleSize||42;if(height({...title,bold:true},1168,titleSize)>74)throw Error('Long title: move lower heading to topic or split source title responsibly');
 put(s,title,56,89,1168,74,{size:titleSize,bold:true,color:C.navy});
 if(d.topic)put(s,d.topic,58,163,1164,45,{size:29,bold:true,color:C.accent});
 line(s,56,213,1168,0,C.line,1.2);
 let y=d.bodyTop??238;
 if(!Number.isFinite(y)||y<218||y>500)throw Error('bodyTop must be within 218–500px');
 for(const b of d.blocks){if((b.before??0)<0||(b.after??0)<0)throw Error('Block spacing must be nonnegative');y+=b.before??0;if(b.type==='paragraphs')y=paraBlock(s,b.items,y,b);else if(b.type==='branches')y=branches(s,b,y);else if(b.type==='table')y=table(s,b,y);else if(b.type==='arrow'){
 if(y+56>650)throw Error('Arrow overflow');s.shapes.add({geometry:'downArrow',position:{left:b.x??366,top:y,width:30,height:38},fill:C.accent,line:{fill:'none',width:0}});y+=60;
 }else throw Error(`Unknown block ${b.type}`);y+=b.after||0;}
 }
 if(d.type!=='knowledge-map'&&d.revealSteps?.length)revealPlan.slides.push({slide:i+1,steps:d.revealSteps});
 if(d.type!=='knowledge-map')text(s,`讲义第${d.page}页`,56,674,600,30,{size:18,color:C.muted});
}
const covered=new Set(usage.map(u=>u.id));const missing=source.units.filter(u=>!covered.has(u.id));if(missing.length)throw Error(`Unplaced source units: ${missing.map(u=>u.id).join(',')}`);
await (await PresentationFile.exportPptx(p)).save(path.join(out,'candidate.pptx'));
await fs.mkdir(path.join(out,'previews'),{recursive:true});
for(let i=0;i<p.slides.items.length;i++){const s=p.slides.items[i],id=String(i+1).padStart(2,'0');const im=await p.export({slide:s,format:'png',scale:1});await fs.writeFile(path.join(out,`previews/${id}.png`),new Uint8Array(await im.arrayBuffer()));}
await fs.writeFile(path.join(out,'layout-review.json'),JSON.stringify(layoutReview,null,2));
await fs.writeFile(path.join(out,'coverage.json'),JSON.stringify({units:source.units.length,usage,summaryEvidence,displayOmissions:source.displayOmissions??[]},null,2));
await fs.writeFile(path.join(out,'reveal-plan.json'),JSON.stringify(revealPlan,null,2));
console.log(JSON.stringify({slides:p.slides.items.length,units:source.units.length,candidate:path.join(out,'candidate.pptx')}));
