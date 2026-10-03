import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {findEssayTemplate,assertGenericRendererAllowed} from '../../skills/politics-lesson-prep/scripts/essay_template_contract.mjs';
test('nested input discovers native workspace contract and blocks generic renderer',()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'essay-template-'));
 try {
  fs.mkdirSync(path.join(root,'.politics-lesson-prep'));
  const config=path.join(root,'.politics-lesson-prep/essay-template.json');
  fs.writeFileSync(config,JSON.stringify({mode:'native-reference'}));
  const input=path.join(root,'.work/trial/questions.json');
  assert.equal(findEssayTemplate(path.dirname(input)),config);
  assert.throws(()=>assertGenericRendererAllowed({input,cwd:root}),/Native essay template required/);
 } finally {fs.rmSync(root,{recursive:true,force:true});}
});
test('explicit template contract blocks generic route outside workspace',()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'essay-template-'));
 try {
  const config=path.join(root,'config.json');fs.writeFileSync(config,'{"mode":"native-reference"}');
  assert.throws(()=>assertGenericRendererAllowed({input:'/tmp/questions.json',cwd:'/tmp',explicit:config}),/Native essay template required/);
  assert.doesNotThrow(()=>assertGenericRendererAllowed({input:path.join(root,'q.json'),cwd:root}));
 } finally {fs.rmSync(root,{recursive:true,force:true});}
});
