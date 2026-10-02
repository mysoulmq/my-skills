// Check internal consistency; an independent subject review must still judge the reasons.
export function validateChoice(q) {
  if (!q.id || !q.stem?.trim() || !Array.isArray(q.options) || q.options.length !== 4)
    throw Error('Choice requires id, stem and four options/statements');
  const keys=q.options.map(o=>o.key);
  if (new Set(keys).size!==4) throw Error(`${q.id}: duplicate option keys`);
  for (const o of q.options) {
    if (!o.text?.trim() || !o.reason?.trim() || !['supported','false','unsupported'].includes(o.verdict))
      throw Error(`${q.id}: each option needs text, verdict and full reason`);
    if (o.verdict!=='supported' && (!o.diagnostic?.trim() || [...o.diagnostic].length>36))
      throw Error(`${q.id}: rejected options need a concise diagnostic (max 36 characters)`);
  }
  const accepted=q.options.filter(o=>o.verdict==='supported').map(o=>o.key).sort();
  if (q.combinations) {
    if(q.combinations.length!==4 || new Set(q.combinations.map(c=>c.key)).size!==4)
      throw Error(`${q.id}: four distinct answer combinations required`);
    for(const c of q.combinations) if(!c.members?.length || new Set(c.members).size!==c.members.length || c.members.some(k=>!keys.includes(k)))
      throw Error(`${q.id}: invalid combination`);
    const matches=q.combinations.filter(c=>[...c.members].sort().join('|')===accepted.join('|'));
    if(matches.length!==1 || matches[0].key!==q.answer) throw Error(`${q.id}: answer not uniquely supported by option judgments`);
  } else if(accepted.length!==1 || accepted[0]!==q.answer) throw Error(`${q.id}: answer not uniquely supported`);
}
