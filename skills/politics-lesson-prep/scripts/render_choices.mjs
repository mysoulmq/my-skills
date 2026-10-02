// Native choice-question page: no separate explanation panel below the question.
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {validateChoice} from './choice_contract.mjs';
import {theme as T,put,putSegments,height,segmentHeight,shape,textWidth,requireFont,hasFont} from './question_style.mjs';
import {writeSpacing,template} from '../../lesson-image-ppt/scripts/template_contract.mjs';
const [input,output]=process.argv.slice(2);
if(!output) throw Error('Usage: render_choices.mjs choices.json output-directory');
const {Presentation,PresentationFile}=await import(pathToFileURL(path.join(process.env.LESSON_NODE_MODULES,'@oai/artifact-tool/dist/artifact_tool.mjs')));
const data=JSON.parse(await fs.readFile(input,'utf8'));
const choiceFonts={source:'KaiTi',option:'SimSun'};
requireFont(choiceFonts.option);
const sourceFontLocallyVerified=hasFont(choiceFonts.source);
// Keep the requested source typeface; font availability is recorded separately.
if(data.questions.some(q=>q.source)&&!sourceFontLocallyVerified)console.warn('KaiTi is not installed locally; source font preview/metrics are unverified.');
const p=Presentation.create({slideSize:T.canvas}), mapping=[],reveal={slides:[]};
const measure=(text,w,size,font=T.fonts.answer)=>height(text,w,{size,font,lineSpacing:1.25});
await fs.mkdir(path.join(output,'previews'),{recursive:true});
for(const q of data.questions){
  validateChoice(q);
  const s=p.slides.add();s._lessonNumber=p.slides.items.length;s.background.fill='#FFFFFF';
  const id=`${q.id}-choice-1`;
  shape(s,'line',40,78,1200,0,{name:`${id}-rule`,color:T.colors.border,width:1});
  put(s,'随堂辨析',40,25,180,{size:28,bold:true,color:T.colors.prompt,name:`${id}-heading`});
  let stemSize=32,optionSize=28,stemH,heights,layouts;
  const sourcePrefix=q.source?(/^[（(【]/u.test(q.source)?q.source:`（${q.source}）`):'';
  const stemSegments=()=>[...(sourcePrefix?[{text:sourcePrefix+' ',size:stemSize-8/3,font:choiceFonts.source,bold:true,color:'#404040'}]:[]),{text:q.stem,size:stemSize,font:T.fonts.material}];
  const labels={'false':'表述错误','unsupported':'不合题意'};
  const diagnostic=o=>`〔${labels[o.verdict]}〕${o.diagnostic}`;
  function rowLayout(o){
    const text=`${o.key}  ${o.text}`,natural=textWidth(text,{size:optionSize,font:choiceFonts.option});
    const optionH=measure(text,1180,optionSize,choiceFonts.option);
    if(o.verdict==='supported')return {height:optionH};
    const dx=48+natural+24,dw=1230-dx;
    const inline=dw>=300 && optionH<=optionSize*1.25+9;
    const x=inline?dx:88,w=inline?dw:1130,dy=inline?3:optionH+6;
    const noteH=measure(diagnostic(o),w,21);
    return {x,w,dy,height:Math.max(optionH,dy+noteH),inline};
  }
  function fit(){
    stemH=segmentHeight(stemSegments(),1190,{size:stemSize,lineSpacing:1.25});
    layouts=q.options.map(rowLayout);heights=layouts.map(r=>r.height);
    return 108+stemH+28+heights.reduce((a,b)=>a+b,0)+3*18<=590;
  }
  while(!fit()&&(stemSize>28||optionSize>26)){if(stemSize>28)stemSize--;else optionSize--;}
  if(!fit()) throw Error(`${q.id}: text exceeds readable choice layout; revise concise diagnostics or supply a justified extended layout, never truncate source`);
  putSegments(s,stemSegments(),40,108,1190,{size:stemSize,lineSpacing:1.25,name:`${id}-stem`});
  let y=108+stemH+28;
  const steps=[[`${id}-answer`]],spare=590-(y+heights.reduce((a,b)=>a+b,0)+3*18),rowGap=18+Math.min(18,spare/3);
  for(const [i,o] of q.options.entries()){
    put(s,`${o.key}  ${o.text}`,48,y,1180,{size:optionSize,font:choiceFonts.option,lineSpacing:1.25,name:`${id}-option-${i}`});
    if(o.verdict!=='supported'){
      const color=o.verdict==='false'?'#B42318':T.colors.prompt;
      const box=layouts[i];
      put(s,diagnostic(o),box.x,y+box.dy,box.w,{size:21,font:T.fonts.answer,lineSpacing:1.25,color,emphasis:o.diagnosticFocus||[],name:`${id}-annotation-${i}`});
      steps.push([`${id}-annotation-${i}`]);
    }
    y+=heights[i]+rowGap;
  }
  if(q.combinations) put(s,q.combinations.map(c=>`${c.key}．${c.members.join('')}`).join('     '),48,616,920,{size:28,font:choiceFonts.option,name:`${id}-combinations`});
  put(s,`答案  ${q.answer}`,1000,632,240,{size:40,bold:true,color:'#C00000',name:`${id}-answer`});
  // Detailed reasoning stays out of the projected text and remains available for review.
  s.speakerNotes.textFrame.setText([...(q.source?[`来源：${q.source}`]:[]),`点击1显示答案；之后按选项顺序显示纠错旁注。`,...q.options.map(o=>`${o.key}：${o.reason}`)].join('\n'));
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
await fs.writeFile(path.join(output,'template-source.json'),JSON.stringify({sha256:template.sha256,sourceFont:choiceFonts.source,sourceFontLocallyVerified}));
console.log(JSON.stringify({slides:mapping.length}));
