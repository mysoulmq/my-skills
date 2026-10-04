// Reserve a right-hand explanation area for every option, regardless of verdict.
// Long options wrap in their own column; explanations never move underneath.
export function choiceColumns(naturalWidth){
  if(!Number.isFinite(naturalWidth)||naturalWidth<0)throw Error('Invalid option text width');
  const optionW=Math.min(naturalWidth+4,734);
  const x=48+optionW+48;
  return {optionW,x,w:1230-x,dy:3};
}
