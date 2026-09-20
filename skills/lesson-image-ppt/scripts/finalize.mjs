import path from 'node:path';
import {pathToFileURL} from 'node:url';
const [workspace,candidate,finalPath,receipt]=process.argv.slice(2);
const skill=process.env.PRESENTATIONS_SKILL;
if(!receipt||!skill||!process.env.LESSON_PYTHON)throw Error('Set PRESENTATIONS_SKILL, LESSON_PYTHON, RUNTIME_NODE_MODULES; arguments: workspace candidate final.pptx receipt.json (absolute paths)');
const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')));
const result=await finalizePresentation({workspaceDir:workspace,candidatePath:candidate,finalPath,receiptPath:receipt,pythonExecutable:process.env.LESSON_PYTHON,integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit'],fontPolicy:{basis:'design',families:[process.env.LESSON_FONT_FAMILY||'Microsoft YaHei'],scriptFonts:{ea:process.env.LESSON_FONT_FAMILY||'Microsoft YaHei'}},verifyArtifactToolImport:true});
console.log(JSON.stringify({finalPath:result.finalPath,receiptPath:result.receiptPath,sha256:result.finalSha256}));
