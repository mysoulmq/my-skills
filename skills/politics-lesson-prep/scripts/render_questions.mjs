import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

const [input, dependency, output, sequenceFile, planFile] = process.argv.slice(2);
if (!output) throw Error('Usage: node render_questions.mjs questions.json lesson-image-ppt-dir output-dir');
const {Presentation, PresentationFile} = await import(pathToFileURL(path.join(process.env.LESSON_NODE_MODULES, '@oai/artifact-tool/dist/artifact_tool.mjs')));
const {text, line, richTextRows} = await import(pathToFileURL(path.resolve(dependency, 'scripts/graphics.mjs')));
const data = JSON.parse(await fs.readFile(input, 'utf8'));
const sequence=sequenceFile ? JSON.parse(await fs.readFile(sequenceFile,'utf8')) : [];
const diagnoses=new Set(sequence.filter(e=>e.stage==='diagnosis').map(e=>e.questionId));
const plan=planFile ? JSON.parse(await fs.readFile(planFile,'utf8')) : null;
const p = Presentation.create({slideSize:{width:1280,height:720}});
const slides = [], reveal = {slides:[]};
await fs.mkdir(path.join(output, 'previews'), {recursive:true});
const measure = (str,w,size,bold=false) => richTextRows(str,w,{size,bold}).length*size*1.15+8;

function put(s,str,x,y,w,{size=27,bold=false,color='#000000',name}={}) {
  const h=measure(str,w,size,bold);
  if(y+h>683)throw Error(`Text overflow on ${s._lessonNumber}: ${name}`);
  text(s,str,x,y,w,h,{size,bold,color,lineSpacing:1.15,sourceId:name});
  return h;
}
function add(q,kind,part) {
  const s=p.slides.add();s._lessonNumber=p.slides.items.length;s.background.fill='#FFFFFF';
  const id=`${q.id}-${kind}-${part}`;
  put(s,`${q.title} · ${kind==='diagnosis'?'先作判断':kind==='material'?'阅读材料':kind==='analysis'?'分析思路':'组织答案'}`,36,20,1208,{size:32,bold:true,color:'#173E52',name:`${id}-title`});
  slides.push({id,questionId:q.id,kind,stage:kind==='diagnosis'?'diagnosis':'teaching',sourceSlide:s._lessonNumber,clicks:[]});
  const cues=plan?.notesByPage?.[id];
  if(!Array.isArray(cues)||cues.length<1||cues.length>3||cues.some(v=>typeof v!=='string'||!v.trim()||[...v].length>35||v.includes('\n'))||cues.reduce((n,v)=>n+[...v].length,0)>90)throw Error(`${id}: supply 1–3 short notesByPage cues, ≤35 characters each and ≤90 total; never truncate`);
  s.speakerNotes.textFrame.setText(cues.join('\n'));
  return s;
}
function paginate(items, height, getHeight) {
  const pages=[];let current=[],used=0;
  for(const item of items) {
    const h=getHeight(item);
    if(h>height)throw Error('One teaching point exceeds available height; split into meaningful subpoints in source data');
    if(current.length&&used+h>height){pages.push(current);current=[];used=0;}
    current.push(item);used+=h;
  }
  if(current.length)pages.push(current);
  return pages;
}
for(const q of data.questions) {
  let material=q.material, materialSize=25;
  while(materialSize>22&&measure(material,560,materialSize)>590)materialSize--;
  if(measure(material,560,materialSize)>590) {
    const sentences=material.match(/[^。！？\n]+[。！？\n]?/gu)||[material];
    const pages=paginate(sentences,580,t=>measure(t,1208,27)+10);
    for(const [i,parts] of pages.entries()){
      const s=add(q,'material',i+1);let y=84;
      for(const [j,t] of parts.entries())y+=put(s,t,36,y,1208,{size:27,name:`${q.id}-material-${i}-${j}`})+10;
    }
    material='材料摘录（全文见前页）\n'+q.analysis.map(a=>a.evidence).join('\n\n');materialSize=24;
    if(measure(material,560,materialSize)>590)throw Error(`${q.id}: evidence excerpts too long for material column`);
  }
  const promptH=measure(q.prompt,606,26,true), top=91+promptH+14;
  if(top>310)throw Error(`${q.id}: prompt too long for split layout`);
  if(diagnoses.has(q.id)){
    if(material!==q.material)throw Error(`${q.id}: diagnostic material requires separate full-text layout`);
    const s=add(q,'diagnosis',1);
    put(s,material,36,84,560,{size:materialSize,name:`${q.id}-diagnostic-material`});
    line(s,615,80,0,596,'#91B4C2',1.2);
    put(s,q.prompt,638,84,606,{size:26,bold:true,name:`${q.id}-diagnostic-prompt`});
    put(s,'先圈出设问限定，再选一处材料说明你的判断。',638,top+28,606,{size:28,color:'#173E52',name:`${q.id}-diagnostic-task`});
  }
  const analysis=[{text:`作答任务：${q.task}`,color:'#173E52'},...q.analysis.map((a,i)=>({text:`${i+1}. ${a.evidence}\n→ ${a.principle}`,color:'#000000',note:a.reason}))];
  const answers=q.answer.map((a,i)=>({text:`${i+1}. ${a.principle}\n${a.application}${a.score!==undefined?`（${a.score}分）`:''}`,item:a}));
  for(const [kind,items] of [['analysis',analysis],['answer',answers]]){
    let size=26;
    while(size>23 && items.reduce((sum,a)=>sum+measure(a.text,606,size)+18,0)>675-top)size--;
    const pages=paginate(items,675-top,a=>measure(a.text,606,size)+18);
    for(const [part,items] of pages.entries()){
      const s=add(q,kind,part+1);put(s,material,36,84,560,{size:materialSize,name:`${q.id}-material`});
      line(s,615,80,0,596,'#91B4C2',1.2);
      put(s,q.prompt,638,84,606,{size:26,bold:true,name:`${q.id}-prompt`});
      let y=top;const steps=[];
      for(const [i,a] of items.entries()){
        const name=`${q.id}-${kind}-${part+1}-${i+1}`;
        if(kind==='answer'){
          // One native rich-text box per complete answer point.
          const h=measure(a.text,606,size);
          const sh=text(s,a.text,638,y,606,h,{size,color:'#000000',lineSpacing:1.15,sourceId:name});
          const rows=richTextRows(a.text,606,{size,color:'#000000'});
          let offset=0;const start=a.text.indexOf(a.item.application),end=start+a.item.application.length;
          // Work at character offsets while preserving wrapped native paragraphs.
          sh.text=rows.map(row=>row.flatMap(run=>Array.from(run.run).map(ch=>{
            while(a.text[offset]==='\n')offset++;
            const at=offset;offset+=ch.length;
            return {run:ch,textStyle:{...run.textStyle,color:at>=start&&at<end?'#00B0F0':at>=end&&a.item.score!==undefined?'#00B050':'#000000'}};
          })));
          y+=h+18;
        } else y+=put(s,a.text,638,y,606,{size,color:a.color,name})+18;
        steps.push([name]);
      }
      reveal.slides.push({slide:s._lessonNumber,steps});slides.at(-1).clicks=steps;
    }
  }
}
await (await PresentationFile.exportPptx(p)).save(path.join(output,'candidate.pptx'));
for(const [i,s] of p.slides.items.entries()){
  const im=await p.export({slide:s,format:'png',scale:1});
  await fs.writeFile(path.join(output,'previews',`${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await im.arrayBuffer()));
}
await fs.writeFile(path.join(output,'slides.json'),JSON.stringify(slides,null,2));
await fs.writeFile(path.join(output,'reveal-plan.json'),JSON.stringify(reveal,null,2));
console.log(JSON.stringify({slides:slides.length,candidate:path.join(output,'candidate.pptx')}));
