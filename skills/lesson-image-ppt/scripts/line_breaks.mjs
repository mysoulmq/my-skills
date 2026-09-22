// Preserve styled glyphs while wrapping at legal Chinese/number boundaries.
export function wrapGlyphs(glyphs, width) {
  const closing=/^[，。；：！？、）】》〉〕］｝”’％%,.!?;:)\]}…]$/;
  const opening=/^[（【《〈〔［｛“‘(\[{]$/;
  const result=[];let paragraph=[];
  function flush(){
    if(!paragraph.length){result.push([]);return;}
    const src=paragraph.map(g=>g.ch).join(''),forbidden=new Set();
    const offsets=[];let offset=0;
    for(const g of paragraph){offsets.push(offset);offset+=g.ch.length;}
    // Numerals, decimal/range expressions, units and enumeration prefixes travel together.
    const tokens=/[A-Za-z]+(?:[0-9]+)?|[0-9]+(?:[.,．][0-9]+)*(?:[—–~～-][0-9]+(?:\.[0-9]+)*)?(?:[%％]|分钟|分|年|月|日|个|项|点|次|倍|万|亿|元|人|页|课|框|目|条)?[、.]?|[①-⑳]/gu;
    for(const m of src.matchAll(tokens)){
      const end=m.index+m[0].length;
      for(let j=1;j<offsets.length;j++)if(offsets[j]>m.index&&offsets[j]<end)forbidden.add(j);
      if(/[、.]$|^[①-⑳]$/.test(m[0])){const j=offsets.indexOf(end);if(j>0)forbidden.add(j);}
    }
    const legal=i=>i===paragraph.length||(!forbidden.has(i)&&!closing.test(paragraph[i].ch)&&!opening.test(paragraph[i-1].ch));
    let start=0;
    while(start<paragraph.length){
      let end=start,used=0;
      while(end<paragraph.length&&used+paragraph[end].width<=width){used+=paragraph[end].width;end++;}
      if(end===paragraph.length){result.push(paragraph.slice(start));break;}
      while(end>start&&!legal(end))end--;
      if(end===start)throw Error('Unbreakable text exceeds column width; widen the column or adjust the layout');
      result.push(paragraph.slice(start,end));start=end;
    }
    paragraph=[];
  }
  for(const g of glyphs){if(g.ch==='\n')flush();else paragraph.push(g);}
  flush();return result;
}
