import test from 'node:test';
import assert from 'node:assert/strict';
import {choiceSteps} from '../../skills/politics-lesson-prep/scripts/choice_animation.mjs';
test('initial question text never enters answer reveal steps',()=>{
  assert.deepEqual(choiceSteps('q1-choice-1',[{verdict:'supported'},{verdict:'false'},{verdict:'unsupported'},{verdict:'supported'}]),[['q1-choice-1-answer'],['q1-choice-1-annotation-1'],['q1-choice-1-annotation-2']]);
});
