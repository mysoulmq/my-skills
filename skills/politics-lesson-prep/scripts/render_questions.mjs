import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {theme as T,put,height,shape,brace,arrow} from './question_style.mjs';
const [input,dependency,output,sequenceFile,planFile]=process.argv.slice(2);
if(!output)throw Error('Usage: render_questions.mjs questions.json dependency-dir output sequence.json plan.json [--layout-only]');
const layoutOnly=process.argv.includes('--layout-only');
const {Presentation,PresentationFile}=await import(pathToFileURL(path.join(process.env.LESSON_NODE_MODULES,'@oai/artifact-tool/dist/artifact_tool.mjs')));
const data=JSON.parse(await fs.readFile(input,'utf8'));
const sequence=sequenceFile?JSON.parse(await fs.readFile(sequenceFile,'utf8')):[];
const plan=planFile?JSON.parse(await fs.readFile(planFile,'utf8')):{};
const diagnoses=new Set(sequence.filter(e=>e.stage==='diagnosis').map(e=>e.questionId));
const p=Presentation.create({slideSize:T.canvas}),slides=[],reveal={slides:[]};
const C=T.colors,F=T.fonts;
const h=(str,w,size=T.type.body,extra={})=>height(str,w,{size,...extra});
await fs.mkdir(path.join(output,'previews'),{recursive:true});
function scorePrompt(q){
 const match=q.prompt.match(/[（(]\s*(\d+(?:\.\d+)?)\s*分\s*[）)]/);
 if(q.totalScore!==undefined){
  if(!Number.isFinite(q.totalScore)||q.totalScore<=0||!q.totalScoreSource)throw Error(`${q.id}: totalScore needs positive number and source`);
  if(match&&Number(match[1])!==q.totalScore)throw Error(`${q.id}: conflicting question total scores`);
  if(q.scoreStatus==='predicted'){
   if(match||!q.scorePrediction?.basis||!q.scorePrediction?.note)throw Error(`${q.id}: invalid predicted score or conflict with source score`);
   return q.prompt+`（${q.totalScore}分）`;
  }
  if(!match)return q.prompt+`（${q.totalScore}分）`;
 }
 return q.prompt;
}
function add(q,kind,part,material,size){
 const s=p.slides.add();s._lessonNumber=p.slides.items.length;s.background.fill=C.background;
 const id=`${q.id}-${kind}-${part}`,prompt=scorePrompt(q);
 slides.push({id,questionId:q.id,kind,stage:kind==='diagnosis'?'diagnosis':'teaching',sourceSlide:s._lessonNumber,clicks:[]});
 const cues=plan.notesByPage?.[id];
 if(!layoutOnly){
  if(!Array.isArray(cues)||!cues.length||cues.length>3||cues.some(v=>typeof v!=='string'||!v.trim()||[...v].length>35||v.includes('\n'))||cues.reduce((n,v)=>n+[...v].length,0)>90)throw Error(`${id}: supply short notesByPage cues; use --layout-only to plan page IDs first`);
  s.speakerNotes.textFrame.setText(cues.join('\n'));
 }
 shape(s,'rect',12,16,578,688,{name:`${id}-material-border`,color:C.border,width:2});
 put(s,material,24,27,554,{size,font:F.material,name:kind==='material'?`${q.id}-material-${part}-body`:`${q.id}-material`});
 const ph=h(prompt,626,T.type.prompt,{bold:true})+16;
 shape(s,'rect',610,16,654,ph,{name:`${id}-prompt-bar`,color:C.prompt,fill:C.prompt,width:0});
 put(s,prompt,624,24,626,{size:T.type.prompt,bold:true,color:C.promptText,name:`${q.id}-prompt`});
 return {s,top:16+ph+24};
}
function paginate(items,limit,heightFn){
 const pages=[];let current=[],used=0;
 for(const item of items){const hh=heightFn(item);if(hh>limit)throw Error('One complete point exceeds map area: split it semantically without dropping original text');
  if(current.length&&used+hh>limit){pages.push(current);current=[];used=0;}current.push(item);used+=hh;
 }if(current.length)pages.push(current);return pages;
}
for(const q of data.questions){
 let material=q.material,size=T.material.fontSize;
 while(size>T.material.minFontSize&&h(material,554,size,{font:F.material})>665)size--;
 if(h(material,554,size,{font:F.material})>665){
  const parts=paginate(material.match(/[^。！？\n]+[。！？\n]?/gu)||[material],650,t=>h(t,554,28,{font:F.material}));
  parts.forEach((items,i)=>add(q,'material',i+1,items.join(''),28));
  material=q.analysis.map(a=>a.evidence).join('\n');size=28;
  if(h(material,554,size,{font:F.material})>665)throw Error(`${q.id}: split evidence excerpts into page-specific groups`);
 }
 const prompt=scorePrompt(q),top=16+h(prompt,626,T.type.prompt,{bold:true})+16+24;
 if(diagnoses.has(q.id)){
  const {s}=add(q,'diagnosis',1,material,size);
  put(s,'审题——\n确定答题格式',644,top,220,{font:F.label,size:28,name:`${q.id}-diagnosis-label`});
  put(s,q.task,894,top,350,{bold:true,name:`${q.id}-diagnosis-task`});
 }
 // Analysis is a bracketed teaching map, not a list of evidence/principle strings.
 const taskH=Math.max(h('审题——\n确定答题格式',160,24,{font:F.label}),h(q.task,426,24,{bold:true}));
 const start=top+taskH+30;
 const ah=a=>h(a.principle,426,24,{bold:true})+Math.max(h(a.evidence,245,24),h(a.reason,295,24))+54;
 for(const [part,items] of paginate(q.analysis,696-start,ah).entries()){
  const {s}=add(q,'analysis',part+1,material,size);const steps=[];
  brace(s,628,top,696-top,`${q.id}-analysis-${part+1}-outer`,C.outerBrace);
  put(s,'审题——\n确定答题格式',650,top,160,{font:F.label,size:24,name:`${q.id}-analysis-${part+1}-task-label`});
  const taskName=`${q.id}-analysis-${part+1}-task`;
  put(s,q.task,838,top,426,{bold:true,focus:q.taskFocus||[],name:taskName});
  steps.push([arrow(s,806,top+22,taskName+'-arrow'),taskName]);let y=start;
  for(const [i,a] of items.entries()){
   const name=`${q.id}-analysis-${part+1}-${i+1}`,ph=h(a.principle,426,24,{bold:true});
   put(s,'原理定位',650,y,150,{font:F.label,size:28,name:name+'-label'});
   const bs=brace(s,822,y,ph,name+'-brace');
   put(s,a.principle,838,y,426,{bold:true,focus:a.principleFocus||[],name:name+'-principle'});
   steps.push([...bs,name+'-principle']);y+=ph+14;
   put(s,a.evidence,650,y,245,{focus:a.evidenceFocus||[],name:name+'-evidence'});
   put(s,a.reason,957,y,295,{name:name+'-reason'});
   steps.push([name+'-evidence',arrow(s,913,y+14,name+'-arrow'),name+'-reason']);
   y+=Math.max(h(a.evidence,245,24),h(a.reason,295,24))+40;
  }
  reveal.slides.push({slide:s._lessonNumber,steps});slides.at(-1).clicks=steps;
 }
 // Complete answer points remain complete, each with native branches and original sample typography.
 const scoreText=a=>a.score===undefined?'':`（${(a.scoreLabel||'本点').replace(/(?:预测|拟分)[：:]?/g,'')}${a.score}分）`;
 const aw=490;
 const bh=a=>Math.max(h(a.branchLabel||'原理与应用',102,22,{bold:true}),h(a.principle,aw,24,{bold:true})+h(a.application,aw,24)+ (a.score===undefined?0:h(scoreText(a),aw,24,{font:F.label,bold:true})))+32;
 for(const [part,items] of paginate(q.answer,696-top,bh).entries()){
  const {s}=add(q,'answer',part+1,material,size);let y=top;const steps=[];
  for(const [i,a] of items.entries()){
   const index=q.answer.indexOf(a)+1,name=`${q.id}-answer-${part+1}-${i+1}`,hh=bh(a)-24;
   put(s,a.branchLabel||'原理与应用',616,y+Math.max(0,(hh-h(a.branchLabel||'原理与应用',102,22,{bold:true}))/2),102,{size:22,bold:true,name:name+'-root'});
   const bs=brace(s,720,y,hh,name+'-brace',C.outerBrace);
   const ph=put(s,a.principle,750,y,aw,{bold:true,focus:a.principleFocus||[],name:name+'-principle'});
   put(s,a.application,750,y+ph+4,aw,{color:C.application,emphasis:a.applicationEmphasis||[],focus:a.applicationFocus||[],name:name+'-application'});
   const group=[name+'-root',...bs,name+'-principle',name+'-application'];
   if(a.score!==undefined){if(!q.scoreBasis||q.scoreBasis.includes('无原始分值'))throw Error(`${q.id}: answer score without basis`);
    put(s,scoreText(a),750,y+ph+h(a.application,aw,24)+4,aw,{font:F.label,bold:true,color:C.score,name:name+'-score'});group.push(name+'-score');}
   steps.push(group);y+=bh(a);
  }
  reveal.slides.push({slide:s._lessonNumber,steps});slides.at(-1).clicks=steps;
 }
}
await fs.writeFile(path.join(output,'slides.json'),JSON.stringify(slides,null,2));
await fs.writeFile(path.join(output,'reveal-plan.json'),JSON.stringify(reveal,null,2));
if(!layoutOnly){
 await (await PresentationFile.exportPptx(p)).save(path.join(output,'candidate.pptx'));
 for(const [i,s] of p.slides.items.entries()){
  const im=await p.export({slide:s,format:'png',scale:1});await fs.writeFile(path.join(output,'previews',`${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await im.arrayBuffer()));
 }
}
console.log(JSON.stringify({slides:slides.length,layoutOnly}));
