import {test} from 'node:test';
import assert from 'node:assert/strict';
import {validateChoice} from '../../skills/politics-lesson-prep/scripts/choice_contract.mjs';
const question=()=>({id:'review-fixture',origin:'document',stem:'原材料甲。原材料乙。',answer:'A',reference:{locator:'fixture / 1',answer:'A',explanation:'参考解释'},review:{status:'passed',conclusion:'逐项复核完成'},options:[
  {key:'A',text:'正确且适用',verdict:'supported',reason:'对应甲',judgment:{statement:'true',materialSupport:'supported',basis:'材料甲支持结论',evidenceQuotes:['原材料甲']}},
  {key:'B',text:'陈述错误',verdict:'false',reason:'关系倒置',diagnostic:'关系倒置',judgment:{statement:'false',materialSupport:'absent',basis:'前后关系颠倒',evidenceQuotes:[]}},
  ...['C','D'].map(key=>({key,text:'正确但无证据',verdict:'unsupported',reason:'缺少限定情境',diagnostic:'材料未体现',judgment:{statement:'true',materialSupport:'absent',basis:'没有所需情境',evidenceQuotes:[]}}))]});
test('reviewed document question is releasable',()=>assert.doesNotThrow(()=>validateChoice(question(),{requireReview:true})));
test('document answer cannot bypass content review',()=>{const q=question();delete q.review;assert.throws(()=>validateChoice(q),/content review/);});
test('unresolved disagreement is blocked even if combination matches',()=>{const q=question();q.review.status='unresolved';assert.throws(()=>validateChoice(q),/disputed/);});
test('lack of material support cannot become a false proposition',()=>{const q=question();q.options[2].verdict='false';assert.throws(()=>validateChoice(q),/distinct/);});
test('invented evidence is blocked',()=>{const q=question();q.options[0].judgment.evidenceQuotes=['原材料丙'];assert.throws(()=>validateChoice(q),/exact stem/);});
test('reference answer changes require an explicit resolution',()=>{const q=question();q.reference.answer='B';assert.throws(()=>validateChoice(q),/reasoned resolution/);q.review.answerChangeReason='原解析错把无证据当成立，已逐项论证';assert.throws(()=>validateChoice(q),/evidence-backed/);q.review.corrections=[{before:'B',after:'A',reason:'原题明确支持A',evidence:[{type:'original-item',locator:'fixture / 材料甲',excerpt:'原材料甲'}]}];assert.doesNotThrow(()=>validateChoice(q));});
test('missing source text does not imply self-authored question',()=>{const q=question();delete q.origin;assert.throws(()=>validateChoice(q,{requireReview:true}),/origin/);});

test('model preference cannot serve as correction authority',()=>{const q=question();q.review.corrections=[{before:'原解释',after:'改解释',reason:'更专业',evidence:[{type:'model-opinion',locator:'模型判断',excerpt:'我认为更好'}]}];assert.throws(()=>validateChoice(q),/actual curriculum/);});

const sourceQuestion=()=>{
 const q=question();
 q.reference.explanation=q.options.map(o=>`${o.key}：${o.reason}。`).join('');
 q.review={status:'source-preserved',conclusion:'Preserved as requested; not independently approved',sourceInstruction:'User requests retaining the supplied explanation',sourceNote:'原答案与解析保留，存在未核定疑点。'};
 for(const o of q.options){o.sourceReason=o.reason;delete o.judgment;}
 return q;
};
test('explicit source preservation retains provenance without fabricated independent judgments',()=>assert.doesNotThrow(()=>validateChoice(sourceQuestion(),{requireReview:true})));
test('source preservation status alone does not bypass provenance checks',()=>{const q=sourceQuestion();delete q.review.sourceInstruction;assert.throws(()=>validateChoice(q),/user instruction/);});
test('source preservation cannot silently change answers or explanations',()=>{
 const q=sourceQuestion();q.reference.answer='B';assert.throws(()=>validateChoice(q),/match the original/);
 const r=sourceQuestion();r.options[0].reason='invented';assert.throws(()=>validateChoice(r),/exact reference excerpt/);
});
test('source preservation still checks answer combinations',()=>{const q=sourceQuestion();q.options[1].verdict='supported';assert.throws(()=>validateChoice(q),/uniquely supported/);});
test('source preservation requires a full source and cannot carry new conclusions',()=>{
 const q=sourceQuestion();q.reference.explanation=null;assert.throws(()=>validateChoice(q),/document answer and explanation/);
 const r=sourceQuestion();r.teachingAdditions=[{content:'new'}];assert.throws(()=>validateChoice(r),/substantive/);
});
