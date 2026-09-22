import {wrapGlyphs} from '../../lesson-image-ppt/scripts/line_breaks.mjs';
// Native editable question-template primitives; font-aware measurement per role.
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
const require=createRequire(path.join(process.env.LESSON_NODE_MODULES,'__question_fonts.cjs'));
const {GlobalFonts,createCanvas}=require('@napi-rs/canvas');
for(const file of JSON.parse(process.env.LESSON_FONT_FILES||'[]'))GlobalFonts.registerFromPath(file);
export const theme=JSON.parse(fs.readFileSync(new URL('../assets/question-theme.json',import.meta.url),'utf8'));
for(const family of new Set(Object.values(theme.fonts)))if(!GlobalFonts.families.some(f=>f.family===family))throw Error(`Missing required question font: ${family}; load its licensed font file before rendering`);
const ctx=createCanvas(2,2).getContext('2d');
export function rows(str,w,{size=24,font=theme.fonts.answer,bold=false,color=theme.colors.ink,focus=[],contrast=[],emphasis=[]}={}){
  for(const word of [...focus,...contrast,...emphasis])if(!word||!str.includes(word))throw Error(`Visual mark absent from text: ${word}`);
  const ranges=words=>words.flatMap(word=>{const r=[];let i=0;while((i=str.indexOf(word,i))>=0){r.push([i,i+word.length]);i+=word.length;}return r;});
  const hi=ranges(focus),red=ranges(contrast),heavy=ranges(emphasis);const glyphs=[];let offset=0;
  for(const ch of str){
    const strong=heavy.some(([a,b])=>offset>=a&&offset<b);
    const highlighted=hi.some(([a,b])=>offset>=a&&offset<b),marked=red.some(([a,b])=>offset>=a&&offset<b);offset+=ch.length;
    ctx.font=`${bold||marked||strong?'bold ':''}${size}px "${font}"`;
    const width=ctx.measureText(ch).width;
    glyphs.push({ch,width,run:ch,textStyle:{typeface:font,bold:bold||marked||strong,color:marked?theme.colors.contrast:color,...(highlighted?{highlight:theme.colors.highlight}:{})}});
  }
  return wrapGlyphs(glyphs,w-8).map(row=>row.map(({ch,width,...run})=>run));
}
export const spacing=opts=>opts.lineSpacing??1.15;
export const height=(str,w,opts={})=>rows(str,w,opts).length*(opts.size||24)*spacing(opts)+8;
export function put(s,str,x,y,w,opts={}){
  const size=opts.size||24,h=height(str,w,opts);
  if(y+h>706)throw Error(`Question text overflow ${opts.name}: bottom ${y+h}`);
  const sh=s.shapes.add({geometry:'textbox',name:opts.name,position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
  sh.text.style={fontSize:size,typeface:opts.font||theme.fonts.answer,color:opts.color||theme.colors.ink,bold:opts.bold||false,wrap:'none',autoFit:'none',lineSpacing:spacing(opts),insets:{top:0,bottom:0,left:0,right:0}};
  sh.text=rows(str,w,opts);return h;
}
export function shape(s,geometry,x,y,w,h,{name,color=theme.colors.innerBrace,fill='none',width=theme.lineWidth}={}){
  return s.shapes.add({geometry,name,position:{left:x,top:y,width:w,height:h},fill,line:{fill:color,width}});
}
export function brace(s,x,y,h,name,color=theme.colors.innerBrace){
  // Three native line segments form a bracket with stable animation target names.
  const names=[name+'-top',name+'-stem',name+'-bottom'];
  shape(s,'line',x,y,10,0,{name:names[0],color});shape(s,'line',x,y,0,h,{name:names[1],color});shape(s,'line',x,y+h,10,0,{name:names[2],color});return names;
}
export function arrow(s,x,y,name){shape(s,'rightArrow',x,y,28,18,{name,color:theme.colors.arrow,fill:theme.colors.arrow,width:1});return name;}
