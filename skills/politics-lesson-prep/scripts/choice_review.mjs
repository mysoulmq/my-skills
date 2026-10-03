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
  if(r?.status==='source-preserved'){
    if(q.origin!=='document'||!filled(q.reference?.answer)||!filled(q.reference?.explanation))fail('source-preserved requires a document answer and explanation');
    const authoritative=r.sourcePolicy==='provided-answer-authoritative';
    if(!filled(r.conclusion)||(!authoritative&&(!filled(r.sourceInstruction)||!filled(r.sourceNote))))fail('source-preserved requires the user instruction, slide note and conclusion, or the authoritative source policy');
    if(q.answer!==q.reference.answer)fail('source-preserved answer must match the original');
    if(!Array.isArray(r.corrections??[])||!Array.isArray(q.teachingAdditions??[])||(r.corrections??[]).length||(q.teachingAdditions??[]).length)fail('source-preserved cannot contain substantive corrections or additions');
    for(const o of q.options){
      if(!filled(o.sourceReason)||!q.reference.explanation.includes(o.sourceReason)||o.reason!==o.sourceReason)
        fail(`option ${o.key}: source-preserved reason must retain an exact reference excerpt`);
    }
    return; // Provenance preservation, not a claim of independent subject approval.
  }
  if(r?.status!=='passed'||!filled(r.conclusion))fail('unresolved or missing content review; do not release a disputed answer');
  if(q.origin==='document'&&q.reference.answer!==null&&q.reference.answer!==q.answer&&!filled(r.answerChangeReason))fail('answer differs from source without a reasoned resolution');
  const corrections=r.corrections??[];
  if(!Array.isArray(corrections))fail('corrections must be an array');
  for(const c of corrections){
    if(!filled(c.before)||!filled(c.after)||!filled(c.reason)||!Array.isArray(c.evidence)||!c.evidence.length)fail('substantive correction needs original, revision and verifiable evidence');
    if(c.evidence.some(e=>!['textbook','curriculum','official-exam','original-item'].includes(e.type)||!filled(e.locator)||!filled(e.excerpt)))fail('correction evidence must identify an actual curriculum/textbook/exam/item passage');
  }
  if(q.origin==='document'&&q.reference.answer!==null&&q.reference.answer!==q.answer&&!corrections.some(c=>c.before===q.reference.answer&&c.after===q.answer))fail('changed answer needs a matching evidence-backed correction');
  for(const o of q.options){
    const j=o.judgment;
    if(!j||!['true','false'].includes(j.statement)||!['supported','absent'].includes(j.materialSupport)||!filled(j.basis))fail(`option ${o.key} needs separate statement/material judgments and reasoning`);
    const expected=j.statement==='false'?'false':j.materialSupport==='supported'?'supported':'unsupported';
    if(o.verdict!==expected)fail(`option ${o.key}: false statement and missing material support must remain distinct`);
    if(!Array.isArray(j.evidenceQuotes)||j.evidenceQuotes.some(x=>!filled(x)||!q.stem.includes(x)))fail(`option ${o.key}: evidence must be an exact stem quotation`);
    if(o.verdict==='supported'&&!j.evidenceQuotes.length)fail(`option ${o.key}: selected option needs material evidence`);
  }
}
