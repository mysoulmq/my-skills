import {assertGenericRendererAllowed} from './essay_template_contract.mjs';
import {role,gap,writeSpacing,template} from '../../lesson-image-ppt/scripts/template_contract.mjs';
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {theme as T,put,putSegments,height,segmentHeight,shape,brace,arrow} from './question_style.mjs';
const [input,dependency,output,sequenceFile,planFile]=process.argv.slice(2);
if(!output)throw Error('Usage: render_questions.mjs questions.json dependency-dir output sequence.json plan.json [--layout-only]');
assertGenericRendererAllowed({input});
const layoutOnly=process.argv.includes('--layout-only');
const {Presentation,PresentationFile}=await import(pathToFileURL(path.join(process.env.LESSON_NODE_MODULES,'@oai/artifact-tool/dist/artifact_tool.mjs')));
const data=JSON.parse(await fs.readFile(input,'utf8'));
const sequence=sequenceFile?JSON.parse(await fs.readFile(sequenceFile,'utf8')):[];
const plan=planFile?JSON.parse(await fs.readFile(planFile,'utf8')):{};
const diagnoses=new Set(sequence.filter(e=>e.stage==='diagnosis').map(e=>e.questionId));
const p=Presentation.create({slideSize:T.canvas}),slides=[],reveal={slides:[]},layoutDecisions=[];
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
  if(!Array.isArray(cues)||!cues.length||cues.length>5||cues.some(v=>typeof v!=='string'||!v.trim()||[...v].length>60||v.includes('\n'))||cues.reduce((n,v)=>n+[...v].length,0)>200)throw Error(`${id}: supply short notesByPage cues; use --layout-only to plan page IDs first`);
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
 const firstSlide=slides.length;
 if(q.layout?.analysisPages&&!q.layout?.reason)throw Error(`${q.id}: separate analysis pages require a concrete teaching reason`);
 const materialLimit=648;
 let material=q.material,size=T.material.fontSize;
 while(size>T.material.minFontSize&&h(material,554,size,{font:F.material})>materialLimit)size--;
 if(h(material,554,size,{font:F.material})>materialLimit){
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
 // Default: material + prompt + answer map on the same slide.
 // Analysis is taught through reveal steps and page-local cues, not duplicated pages.
 if(q.layout?.analysisPages===true){
 // Explicitly justified expanded analysis remains available for exceptional lessons.
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
 }
 // The human sample treats the answer as a scoring rubric: number, theory +
 // theory score, then material + material score. Semantic branch labels remain
 // in data/notes but do not steal horizontal space from the final answer.
 const cleanLabel=(value,fallback)=>(value||fallback).replace(/(?:预测|拟分)[：:]?/g,'');
 const scoreText=(value,label)=>value===undefined?'':`（${cleanLabel(label,'本点')}${value}分）`;
 const anyScore=a=>a.principleScore!==undefined||a.applicationScore!==undefined||a.score!==undefined;
 const aw=590,answerX=650,numberX=616,numberW=30;
 const answerSize=role('question.theory.2.1').size,answerStyle={size:answerSize,lineSpacing:role('question.theory.2.1').lineSpacing};
 const innerGap=8,pointGap=22;
 const principleSegments=a=>[
  {text:a.principle,font:F.answer,size:answerSize,bold:true,color:C.ink,focus:a.principleFocus||[]},
  ...(a.principleScore===undefined?[]:[{text:` ${scoreText(a.principleScore,a.principleScoreLabel||'知识')}`,font:F.label,size:answerSize,bold:true,color:C.score}]),
 ];
 const applicationSegments=a=>[
  {text:a.application,font:F.answer,size:answerSize,bold:false,color:C.application,focus:a.applicationFocus||[],emphasis:a.applicationEmphasis||[]},
  ...(a.applicationScore===undefined?[]:[{text:` ${scoreText(a.applicationScore,a.applicationScoreLabel||'对应材料-')}`,font:F.label,size:answerSize,bold:true,color:C.score}]),
  ...(a.score===undefined?[]:[{text:` ${scoreText(a.score,a.scoreLabel||'本点')}`,font:F.label,size:answerSize,bold:true,color:C.score}]),
 ];
 const contentH=a=>segmentHeight(principleSegments(a),aw,answerStyle)+innerGap+segmentHeight(applicationSegments(a),aw,answerStyle);
 const bh=a=>contentH(a)+pointGap;
 // A gap is needed between points, not after the final point.
 let answerNumber=0;
 for(const [part,items] of paginate(q.answer,696-top+pointGap,bh).entries()){
  const {s}=add(q,'answer',part+1,material,size);let y=top+20;const steps=[];
  for(const [i,a] of items.entries()){
   if(anyScore(a)&&(!q.scoreBasis||q.scoreBasis.includes('无原始分值')))throw Error(`${q.id}: visible answer score without source basis`);
   if(a.score!==undefined&&(a.principleScore!==undefined||a.applicationScore!==undefined))throw Error(`${q.id}: use split scores or legacy branch score, not both`);
   const name=`${q.id}-answer-${part+1}-${i+1}`;
   const numberName=name+'-number';
   answerNumber++;
   put(s,`${answerNumber}.`,numberX,y,numberW,{...answerStyle,bold:true,name:numberName});
   const ph=putSegments(s,principleSegments(a),answerX,y,aw,{...answerStyle,name:name+'-principle'});
   putSegments(s,applicationSegments(a),answerX,y+ph+innerGap,aw,{...answerStyle,name:name+'-application'});
   const theoryGroup=[numberName,name+'-principle'];
   const applicationGroup=[name+'-application'];
   steps.push(theoryGroup,applicationGroup);y+=bh(a);
  }
  reveal.slides.push({slide:s._lessonNumber,steps});slides.at(-1).clicks=steps;
 }
 const pages=slides.slice(firstSlide);
 layoutDecisions.push({questionId:q.id,mode:q.layout?.analysisPages?'expanded-analysis':'same-page-reveal',pages:pages.map(x=>x.id),materialHeight:h(q.material,554,size,{font:F.material}),materialLimit,answerHeight:q.answer.reduce((n,a)=>n+bh(a),0)-pointGap,answerLimit:696-top,reasons:[...(pages.some(x=>x.kind==='material')?['full material exceeds measured area at minimum readable font']:[]),...(pages.filter(x=>x.kind==='answer').length>1?['complete answer points exceed measured area with scoring-rubric typography']:[]),...(q.layout?.analysisPages?[q.layout.reason]:[])]});
}
await fs.writeFile(path.join(output,'layout-decisions.json'),JSON.stringify(layoutDecisions,null,2));
await fs.writeFile(path.join(output,'slides.json'),JSON.stringify(slides,null,2));
await fs.writeFile(path.join(output,'reveal-plan.json'),JSON.stringify(reveal,null,2));
if(!layoutOnly){
 await (await PresentationFile.exportPptx(p)).save(path.join(output,'candidate.pptx'));
 writeSpacing(path.join(output,'candidate.pptx'));
 await fs.writeFile(path.join(output,'template-source.json'),JSON.stringify({sha256:template.sha256}));
 for(const [i,s] of p.slides.items.entries()){
  const im=await p.export({slide:s,format:'png',scale:1});await fs.writeFile(path.join(output,'previews',`${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await im.arrayBuffer()));
 }
}
console.log(JSON.stringify({slides:slides.length,layoutOnly}));
