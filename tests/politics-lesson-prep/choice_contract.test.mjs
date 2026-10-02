import {test} from 'node:test';
import assert from 'node:assert/strict';
import {validateChoice} from '../../skills/politics-lesson-prep/scripts/choice_contract.mjs';
const example=()=>({id:'x',stem:'材料与设问',answer:'B',options:[
  {key:'①',text:'观点一',verdict:'supported',reason:'证据一'},
  {key:'②',text:'观点二',verdict:'false',reason:'关系颠倒',diagnostic:'决定方向颠倒'},
  {key:'③',text:'观点三',verdict:'supported',reason:'证据三'},
  {key:'④',text:'观点四',verdict:'unsupported',reason:'缺少此证据',diagnostic:'材料未体现'}],
  combinations:[{key:'A',members:['①','②']},{key:'B',members:['①','③']},{key:'C',members:['②','④']},{key:'D',members:['③','④']}]});
test('unique combination follows individual judgments',()=>assert.doesNotThrow(()=>validateChoice(example())));
test('mismatched answer is rejected',()=>{const q=example();q.answer='A';assert.throws(()=>validateChoice(q));});
test('duplicate correct combinations are rejected',()=>{const q=example();q.combinations[0].members=['①','③'];assert.throws(()=>validateChoice(q));});
test('wrong option must have nearby concise explanation',()=>{const q=example();delete q.options[1].diagnostic;assert.throws(()=>validateChoice(q));});
test('correct but irrelevant option is distinct from false claim',()=>{const q=example();assert.doesNotThrow(()=>validateChoice(q));q.options[3].verdict='supported';assert.throws(()=>validateChoice(q));});
