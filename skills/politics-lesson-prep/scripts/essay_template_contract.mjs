import fs from 'node:fs';
import path from 'node:path';

export function findEssayTemplate(start) {
  let dir = path.resolve(start);
  for (;;) {
    const file = path.join(dir, '.politics-lesson-prep', 'essay-template.json');
    if (fs.existsSync(file)) return file;
    const parent = path.dirname(dir);
    if (parent === dir) return null;
    dir = parent;
  }
}
export function assertGenericRendererAllowed({input, cwd=process.cwd(), explicit=process.env.LESSON_ESSAY_TEMPLATE}) {
  const file = explicit || findEssayTemplate(path.dirname(path.resolve(input))) || findEssayTemplate(cwd);
  if (!file) return;
  const contract = JSON.parse(fs.readFileSync(file, 'utf8'));
  if (contract.mode === 'native-reference') {
    throw new Error(`Native essay template required by ${file}. Import/duplicate its original slides and replace content in place; render_questions.mjs reconstructs a different layout and must not be used for this workspace. See references/native-essay-template.md. This is a rendering-route change, not a reason to stop lesson preparation.`);
  }
}
