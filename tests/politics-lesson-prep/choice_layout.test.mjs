import test from 'node:test';
import assert from 'node:assert/strict';
import {choiceColumns} from '../../skills/politics-lesson-prep/scripts/choice_layout.mjs';
test('short explanations remain close and strictly right of option box',()=>{
 const b=choiceColumns(320);assert.equal(b.x,48+b.optionW+48);assert.equal(b.dy,3);
});
test('long option wraps without sending explanation below it',()=>{
 const b=choiceColumns(1800);assert.equal(b.optionW,734);assert.equal(b.w,400);assert.equal(b.dy,3);
});
