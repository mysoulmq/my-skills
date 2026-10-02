// Release gate for an auditable teaching judgment, not a subject-matter oracle.
const filled=v=>typeof v==='string'&&v.trim().length>0;
export function validateChoiceReview(q) {
  const fail=message=>{throw Error(`${q.id}: ${message}`);};
  if(!['document','authored'].includes(q.origin))fail('record document/authored origin; missing provenance is not evidence of authorship');
  if(q.origin==='document'){
    const r=q.reference;
    if(!r||!filled(r.locator)||!Object.hasOwn(r,'answer')||!Object.hasOwn(r,'explanation'))fail('preserve document locator, original answer and explanation (null if absent)');
    for(const field of ['answer','explanation'])if(r[field]!==null&&!filled(r[field]))fail(`invalid reference ${field}`);
  }
  const r=q.review;
  if(r?.status!=='passed'||!filled(r.conclusion))fail('unresolved or missing content review; do not release a disputed answer');
  if(q.origin==='document'&&q.reference.answer!==null&&q.reference.answer!==q.answer&&!filled(r.answerChangeReason))fail('answer differs from source without a reasoned resolution');
  for(const o of q.options){
    const j=o.judgment;
    if(!j||!['true','false'].includes(j.statement)||!['supported','absent'].includes(j.materialSupport)||!filled(j.basis))fail(`option ${o.key} needs separate statement/material judgments and reasoning`);
    const expected=j.statement==='false'?'false':j.materialSupport==='supported'?'supported':'unsupported';
    if(o.verdict!==expected)fail(`option ${o.key}: false statement and missing material support must remain distinct`);
    if(!Array.isArray(j.evidenceQuotes)||j.evidenceQuotes.some(x=>!filled(x)||!q.stem.includes(x)))fail(`option ${o.key}: evidence must be an exact stem quotation`);
    if(o.verdict==='supported'&&!j.evidenceQuotes.length)fail(`option ${o.key}: selected option needs material evidence`);
  }
}
