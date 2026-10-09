import {role} from './template_contract.mjs';

// Semantic level survives pagination: a point in the body has the same style
// as a point in the page's topic slot. Do not infer levels from numbering.
export function headingStyle(level='point') {
  const r=role('lesson.subtitle.2');
  return {size:r.size-(level==='subpoint'?2:0),bold:true,color:r.color};
}

export function prepareParagraphs(blocks, units) {
  return structuredClone(blocks).map(b=>{
    if(b.type!=='paragraphs')return b;
    let level=null;
    b.items=b.items.map(input=>{
      const o=typeof input==='string'?{ref:input}:input;
      const u=units.get(o.ref);
      if(u?.kind==='heading') {
        if(!u.level)throw Error(`Heading ${u.id}: declare semantic level before layout`);
        if(['point','subpoint'].includes(u.level)) {
          level=u.level;
          return {...o,...headingStyle(level),bullet:false,indent:level==='subpoint'?24:0,gap:12,semanticHeading:level,keepGap:true};
        }
        level=null;
      }
      if(level)return {...o,indent:Math.max(o.indent??0,level==='subpoint'?48:24),gap:o.gap??28};
      return o;
    });
    return b;
  });
}
