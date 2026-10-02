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
test('reference answer changes require an explicit resolution',()=>{const q=question();q.reference.answer='B';assert.throws(()=>validateChoice(q),/reasoned resolution/);q.review.answerChangeReason='原解析错把无证据当成立，已逐项论证';assert.doesNotThrow(()=>validateChoice(q));});
test('missing source text does not imply self-authored question',()=>{const q=question();delete q.origin;assert.throws(()=>validateChoice(q,{requireReview:true}),/origin/);});
