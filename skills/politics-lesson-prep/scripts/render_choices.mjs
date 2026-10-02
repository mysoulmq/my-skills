// Native choice-question page: no separate explanation panel below the question.
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {validateChoice} from './choice_contract.mjs';
import {theme as T,put,height,shape} from './question_style.mjs';
import {writeSpacing,template} from '../../lesson-image-ppt/scripts/template_contract.mjs';
const [input,output]=process.argv.slice(2);
if(!output) throw Error('Usage: render_choices.mjs choices.json output-directory');
const {Presentation,PresentationFile}=await import(pathToFileURL(path.join(process.env.LESSON_NODE_MODULES,'@oai/artifact-tool/dist/artifact_tool.mjs')));
const data=JSON.parse(await fs.readFile(input,'utf8'));
const p=Presentation.create({slideSize:T.canvas}), mapping=[],reveal={slides:[]};
const measure=(text,w,size,font=T.fonts.answer)=>height(text,w,{size,font,lineSpacing:1.25});
await fs.mkdir(path.join(output,'previews'),{recursive:true});
for(const q of data.questions){
  validateChoice(q);
  const s=p.slides.add();s._lessonNumber=p.slides.items.length;s.background.fill='#FFFFFF';
  const id=`${q.id}-choice-1`;
  shape(s,'line',40,78,1200,0,{name:`${id}-rule`,color:T.colors.border,width:1});
  put(s,'随堂辨析',40,25,180,{size:28,bold:true,color:T.colors.prompt,name:`${id}-heading`});
  if(q.source) put(s,q.source,245,34,985,{size:18,color:'#596873',name:`${id}-source`});
  let stemSize=32,optionSize=28,stemH,heights;
  const labels={'false':'表述错误','unsupported':'不合题意'};
  const diagnostic=o=>`${labels[o.verdict]}：${o.diagnostic}`;
  function fit(){
    stemH=measure(q.stem,1190,stemSize,T.fonts.material);
    heights=q.options.map(o=>Math.max(measure(`${o.key}  ${o.text}`,770,optionSize,T.fonts.material),o.verdict==='supported'?0:measure(diagnostic(o),350,22)));
    return 108+stemH+28+heights.reduce((a,b)=>a+b,0)+3*18<=590;
  }
  while(!fit()&&(stemSize>28||optionSize>26)){if(stemSize>28)stemSize--;else optionSize--;}
  if(!fit()) throw Error(`${q.id}: text exceeds readable choice layout; revise concise diagnostics or supply a justified extended layout, never truncate source`);
  put(s,q.stem,40,108,1190,{size:stemSize,font:T.fonts.material,lineSpacing:1.25,name:`${id}-stem`});
  let y=108+stemH+28;
  const steps=[[`${id}-answer`]],spare=590-(y+heights.reduce((a,b)=>a+b,0)+3*18),rowGap=18+Math.min(18,spare/3);
  for(const [i,o] of q.options.entries()){
    put(s,`${o.key}  ${o.text}`,48,y,770,{size:optionSize,font:T.fonts.material,lineSpacing:1.25,name:`${id}-option-${i}`});
    if(o.verdict!=='supported'){
      const color=o.verdict==='false'?'#B42318':T.colors.prompt;
      shape(s,'line',858,y+3,0,heights[i]-6,{name:`${id}-annotation-line-${i}`,color,width:2});
      put(s,diagnostic(o),876,y,350,{size:22,lineSpacing:1.25,color,name:`${id}-annotation-${i}`});
      steps.push([`${id}-annotation-line-${i}`,`${id}-annotation-${i}`]);
    }
    y+=heights[i]+rowGap;
  }
  if(q.combinations) put(s,q.combinations.map(c=>`${c.key}．${c.members.join('')}`).join('     '),48,616,920,{size:28,font:T.fonts.material,name:`${id}-combinations`});
  put(s,`答案  ${q.answer}`,1020,640,220,{size:30,bold:true,color:T.colors.prompt,name:`${id}-answer`});
  // Detailed reasoning stays out of the projected text and remains available for review.
  s.speakerNotes.textFrame.setText([`来源：${q.source||'自编训练，非真题'}`,`点击1显示答案；之后按选项顺序显示纠错旁注。`,...q.options.map(o=>`${o.key}：${o.reason}`)].join('\n'));
  mapping.push({id,questionId:q.id,kind:'choice',stage:'teaching',sourceSlide:s._lessonNumber,clicks:steps});
  reveal.slides.push({slide:s._lessonNumber,steps});
}
await (await PresentationFile.exportPptx(p)).save(path.join(output,'candidate.pptx'));
writeSpacing(path.join(output,'candidate.pptx'));
for(const [i,s] of p.slides.items.entries()){
  const im=await p.export({slide:s,format:'png',scale:1});
  await fs.writeFile(path.join(output,'previews',`${i+1}.png`),new Uint8Array(await im.arrayBuffer()));
}
await fs.writeFile(path.join(output,'slides.json'),JSON.stringify(mapping,null,2));
await fs.writeFile(path.join(output,'reveal-plan.json'),JSON.stringify(reveal,null,2));
await fs.writeFile(path.join(output,'template-source.json'),JSON.stringify({sha256:template.sha256}));
console.log(JSON.stringify({slides:mapping.length}));
