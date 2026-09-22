// Measured spacing presets: no content, font, ordering, or page-count decisions.
export function fitSpacing(blocks, available, measure, profile='comfortable') {
  if(!['comfortable','preserve'].includes(profile))throw Error(`Unknown spacingProfile: ${profile}`);
  const base=structuredClone(blocks),target=structuredClone(blocks),adjustments=[];
  const grow=(obj,key,current,preferred)=>{
    obj[key]=current;
    if(preferred>current)adjustments.push({obj,key,base:current,delta:preferred-current});
  };
  for(const b of target){
    if(b.type==='paragraphs'){
      const n=b.items.length,preferred=n===2?44:n===3?36:n===4?28:24;
      b.items=b.items.map(v=>typeof v==='string'?{ref:v}:v);
      b.items.forEach((v,i)=>grow(v,'gap',v.gap??b.gap??24,i<n-1?preferred:24));
      if(n<=3)grow(b,'before',b.before??0,12);
    }else if(b.type==='branches'){
      grow(b,'gap',b.gap??32,48);grow(b,'before',b.before??0,10);
    }else if(b.type==='table')grow(b,'before',b.before??0,10);
  }
  const used=list=>list.reduce((n,b)=>n+(b.before??0)+measure(b)+(b.after??0),0);
  const baseline=used(base);
  for(const a of adjustments)a.obj[a.key]=a.base+a.delta;
  const preferred=used(target),extra=preferred-baseline;
  const fraction=profile==='preserve'?0:extra>0?Math.max(0,Math.min(1,(available-baseline)/extra)):1;
  for(const a of adjustments)a.obj[a.key]=a.base+Math.floor(a.delta*fraction);
  const result=profile==='preserve'?base:target;
  return {blocks:result,review:{profile,available,baseline,preferred,used:used(result),fraction,needsRepagination:baseline>available}};
}
