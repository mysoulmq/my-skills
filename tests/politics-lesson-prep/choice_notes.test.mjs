import {test} from 'node:test';
import assert from 'node:assert/strict';
import {choiceNotes} from '../../skills/politics-lesson-prep/scripts/choice_notes.mjs';
const base = {id:'synthetic',options:[{key:'A',reason:'原解析依据'}]};
test('source-based teaching notes do not invent change notices',()=>{
  const notes=choiceNotes(base);
  assert.ok(notes.includes('A：原解析依据'));
  assert.ok(!notes.includes('补充：')&&!notes.includes('修正：'));
});
test('necessary additions and corrections reach slide notes with reasons and provenance',()=>{
  const notes=choiceNotes({...base,teachingAdditions:[{content:'补足限定',reason:'原解析省略限定',basis:'合成材料第二句'}],review:{corrections:[{before:'甲',after:'乙',reason:'原题错配',evidence:[{locator:'合成题原答案'}]}]}});
  for(const text of ['补充：补足限定','原因：原解析省略限定','依据：合成材料第二句','修正：甲→乙','原因：原题错配','依据：合成题原答案'])assert.ok(notes.includes(text));
});
test('unsupported substantive additions cannot silently render',()=>{
  assert.throws(()=>choiceNotes({...base,teachingAdditions:[{content:'新推断',reason:'需要补充'}]}),/requires/);
});
