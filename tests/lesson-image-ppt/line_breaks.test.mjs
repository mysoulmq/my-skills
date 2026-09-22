import assert from 'node:assert/strict';
import {wrapGlyphs} from '../../skills/lesson-image-ppt/scripts/line_breaks.mjs';
const samples=['①坚持实践，推动发展。②遵循规律（具体条件）。','2026年增长3.5%，每课40分钟，完成12个任务。','他说：“认识有反复性！”然后继续。','范围10—20，比例12.5%，含1000人。'];
for(const text of samples)for(const width of [9,12,17]){
 const rows=wrapGlyphs(Array.from(text,ch=>({ch,width:1,style:'retained'})),width);
 assert.equal(rows.flat().map(g=>g.ch).join(''),text);
 for(const row of rows){assert.ok(row.length<=width);assert.ok(!/^[，。；：！？、）】》”’％%,.!?;:)\]}]/.test(row[0].ch));assert.ok(!/[（【《“‘(\[]$/.test(row.at(-1).ch));assert.ok(row.every(g=>g.style==='retained'));}
 const joined=rows.map(row=>row.map(g=>g.ch).join('')).join('\n');
 for(const token of ['2026年','3.5%','40分钟','12个','10—20','12.5%','1000人'])if(text.includes(token))assert.ok(joined.includes(token),joined);
 assert.ok(!/[①②]\n/.test(joined));
}
assert.throws(()=>wrapGlyphs(Array.from('123456789年',ch=>({ch,width:1})),5),/Unbreakable/);
console.log('Chinese boundaries, numeric units, enumeration and style preservation passed');
