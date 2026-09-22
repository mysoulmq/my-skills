import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const script=fileURLToPath(new URL('./template_contract.py',import.meta.url));
export const templatePath=process.env.LESSON_TEMPLATE_PPTX||fileURLToPath(new URL('../assets/teaching-template.pptx',import.meta.url));
export const template=JSON.parse(execFileSync(process.env.LESSON_PYTHON||'python3',[script,'read',templatePath],{encoding:'utf8'}));
export function role(name){const r=template.roles[name];if(!r)throw Error(`Missing named template object: ${name}`);return r;}
export function gap(a,b){const x=role(a),y=role(b),n=y.y-x.y-x.cy;if(!Number.isFinite(n)||n<0)throw Error(`Invalid template gap: ${a} / ${b}`);return n;}
const spacing={};
export function recordSpacing(page,name,ratio){spacing[`${page}:${name}`]=ratio;}
export function writeSpacing(file){execFileSync(process.env.LESSON_PYTHON||'python3',[script,'patch',file,JSON.stringify(spacing)]);}
