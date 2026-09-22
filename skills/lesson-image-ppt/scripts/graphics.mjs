import {role,recordSpacing} from './template_contract.mjs';
import {wrapGlyphs} from './line_breaks.mjs';
import {createRequire} from 'node:module';
import path from 'node:path';
import fs from 'node:fs';
const require=createRequire(path.join(process.env.LESSON_NODE_MODULES,'__resolver.cjs'));
const {GlobalFonts,createCanvas}=require('@napi-rs/canvas');
const fontPaths=JSON.parse(process.env.LESSON_FONT_FILES||'[]');
if(!fontPaths.length)throw Error('Set LESSON_FONT_FILES to local licensed font paths');
for(const f of fontPaths){if(!fs.existsSync(f))throw Error(`Missing font: ${f}`);GlobalFonts.registerFromPath(f);}
export const FONT=process.env.LESSON_FONT_FAMILY||role('lesson.body.2.1').font;
export const C={bg:'#FCFDFE',ink:role('lesson.body.2.1').color,navy:role('lesson.title.2').color,accent:role('lesson.subtitle.2').color,muted:'#627B89',line:'#91B4C2',light:'#EAF3F7',warm:'#A15C23'};
export const recorded=[];
const ctx=createCanvas(10,10).getContext('2d');
function richLines(str,width,size=34,bold=false,emphasis=[],focus=[],contrast=[],italicAfter=''){
  const src=String(str),mask=new Set(),fm=new Set(),cm=new Set();
  const separatorAt=italicAfter?src.indexOf(italicAfter):-1;
  const italicAt=separatorAt<0?Infinity:separatorAt+italicAfter.length;
  for(const [words,set] of [[focus,fm],[contrast,cm]])for(const word of words){let i=0;while(word&&(i=src.indexOf(word,i))>=0){for(let k=i;k<i+word.length;k++)set.add(k);i+=word.length;}}
  for(const word of emphasis){let i=0;while(word&&(i=src.indexOf(word,i))>=0){for(let k=i;k<i+word.length;k++)mask.add(k);i+=word.length;}}
  let offset=0;const glyphs=Array.from(src).map(ch=>{const hi=mask.has(offset),fc=fm.has(offset),ct=cm.has(offset),it=offset>=italicAt;offset+=ch.length;ctx.font=`${it?'italic ':''}${bold||hi||ct?'bold ':''}${size}px "${FONT}"`;return {ch,hi,fc,ct,it,width:ctx.measureText(ch).width};});
  return wrapGlyphs(glyphs,width-Math.min(8,width*0.1));
}
export function linesOf(str,width,size=34,bold=false,emphasis=[],italicAfter=''){return richLines(str,width,size,bold,emphasis,[],[],italicAfter).map(row=>row.map(x=>x.ch).join(''));}
export function richTextRows(str,width,{size=34,bold=false,color=C.ink,emphasis=[],focus=[],contrast=[],italicAfter=''}={}){
  const rows=richLines(str,width,size,bold,emphasis,focus,contrast,italicAfter);
  return rows.map(row=>{
    const runs=[];for(const g of row){const last=runs.at(-1);if(last&&last.hi===g.hi&&last.fc===g.fc&&last.ct===g.ct&&last.it===g.it)last.run+=g.ch;else runs.push({run:g.ch,hi:g.hi,fc:g.fc,ct:g.ct,it:g.it});}
    return runs.map(({run,hi,fc,ct,it})=>({run,textStyle:{bold:bold||hi||ct,italic:it,color:ct?'#FF0000':hi?C.accent:color,...(fc?{highlight:'#FFFF00'}:{}),typeface:FONT}}));
  });
}
export function text(s,str,x,y,w,h,{size=34,bold=false,color=C.ink,align='left',valign='top',fill='none',stroke='none',pad=0,sourceId='',emphasis=[],focus=[],contrast=[],italicAfter='',lineSpacing=role('lesson.body.2.1').lineSpacing}={}){
  const sh=s.shapes.add({geometry:'textbox',name:sourceId||`text-${s.id}-${s.shapes.items.length}`,position:{left:x,top:y,width:w,height:h},fill,line:{fill:stroke,width:stroke==='none'?0:1.2}});
  sh.text.style={typeface:FONT,fontSize:size,bold,color,alignment:align,verticalAlignment:valign,autoFit:'none',wrap:'none',lineSpacing,insets:{top:pad,bottom:pad,left:pad,right:pad}};
  recordSpacing(s._lessonNumber,sourceId||`text-${s.id}-${s.shapes.items.length-1}`,lineSpacing);
  sh.text=richTextRows(str,w-2*pad,{size,bold,color,emphasis,focus,contrast,italicAfter});
  if(sourceId) recorded.push({slide:s._lessonNumber,id:sourceId,text:String(str)});
  return sh;
}
export function line(s,x,y,w,h,color=C.line,width=2){return s.shapes.add({geometry:'line',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:color,width}});}
export function connect(s,a,b,{arrow=false,kind='elbow',from='right',to='left',color=C.line}={}){
  return s.shapes.connect(a,b,{kind,fromSide:from,toSide:to,line:{fill:color,width:2.3},...(arrow?{tail:{type:'triangle',width:'sm',length:'sm'}}:{})});
}
export function node(s,label,x,y,w,h,{size=32,...rest}={}){return text(s,label,x,y,w,h,{size,bold:true,color:C.accent,fill:C.light,stroke:C.line,pad:15,align:'center',valign:'middle',...rest});}
export function branches(s,{root,items,y=244,bottom=645,rootWidth=230,bodyX=362,rootSize=31,size=34,gap=24,rootId='',bodyWidth=862,heights=null}){
  const hs=heights||items.map(it=>Math.ceil(linesOf(it.text,bodyWidth,it.size||size,it.bold||false,it.emphasis||[]).length*(it.size||size)*1.42)+10);
  const needed=hs.reduce((a,b)=>a+b,0)+gap*(items.length-1);
  if(needed>bottom-y+3)throw new Error(`Slide ${s._lessonNumber} branch height ${needed} exceeds ${bottom-y}`);
  const start=y+(bottom-y-needed)/2;
  const rh=Math.max(88,linesOf(root,rootWidth-30,rootSize,true).length*rootSize*1.45+26);
  const r=node(s,root,56,start+needed/2-rh/2,rootWidth,rh,{size:rootSize,sourceId:rootId});
  let yy=start;
  items.forEach((it,i)=>{
    const leaf=text(s,it.text,bodyX,yy,bodyWidth,hs[i],{size:it.size||size,sourceId:it.id||'',emphasis:it.emphasis||[],bold:it.bold||false});
    connect(s,r,leaf); yy+=hs[i]+gap;
  });
  return r;
}
export function para(s,item,x,y,w,{size=34,gap=20,...opts}={}){
  const h=Math.ceil(linesOf(item.text,w,size,opts.bold,item.emphasis||[]).length*size*1.42)+9;
  text(s,item.text,x,y,w,h,{size,sourceId:item.id||'',emphasis:item.emphasis||[],...opts});
  return y+h+gap;
}
