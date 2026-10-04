import fs from 'node:fs';
export const preset=JSON.parse(fs.readFileSync(new URL('../assets/choice-animation.json',import.meta.url),'utf8'));
export function choiceSteps(id,options){
  if(preset.version!==1 || preset.effect!=='appear' || preset.trigger!=='click' || JSON.stringify(preset.initial)!==JSON.stringify(['stem','options','combinations']) || JSON.stringify(preset.steps)!==JSON.stringify(['answer','annotations-in-option-order']))throw Error('Unsupported choice animation preset; update writer/checker and qualify playback before use');
  return [[`${id}-answer`],...options.flatMap((o,i)=>o.verdict==='supported'?[]:[[`${id}-annotation-${i}`]])];
}
