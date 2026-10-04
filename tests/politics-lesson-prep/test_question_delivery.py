import sys
import tempfile
import unittest
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'skills/politics-lesson-prep/scripts'))
from check_question_slides import check
from check_source_delivery import check as check_sources


class ActualQuestionDeliveryTests(unittest.TestCase):
    def write(self, path, knowledge='1. 原理全句', hidden=False):
        p='http://schemas.openxmlformats.org/presentationml/2006/main'
        a='http://schemas.openxmlformats.org/drawingml/2006/main'
        r='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
        def shape(id, text, name=''):
            return f'<p:sp><p:nvSpPr><p:cNvPr id="{id}" name="{name}"/></p:nvSpPr><a:p><a:r><a:t>{escape(text)}</a:t></a:r></a:p></p:sp>'
        contents=[shape(1,'1. 材料原文')+shape(2,knowledge)+shape(3,'材料原文设问分析任务'),
                  shape(4,'1.','q-answer-1-number')+shape(5,'答案原理答案应用')]
        with ZipFile(path,'w') as z:
            z.writestr('ppt/presentation.xml',f'<p:presentation xmlns:p="{p}" xmlns:r="{r}"><p:sldIdLst><p:sldId id="256" r:id="r1"/><p:sldId id="257" r:id="r2"/></p:sldIdLst></p:presentation>')
            z.writestr('ppt/_rels/presentation.xml.rels',f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="r1" Target="slides/slide1.xml" Type="{r}/slide"/><Relationship Id="r2" Target="slides/slide2.xml" Type="{r}/slide"/></Relationships>')
            for i,text in enumerate(contents,1):
                z.writestr(f'ppt/slides/slide{i}.xml',f'<p:sld xmlns:p="{p}" xmlns:a="{a}" show="{0 if hidden else 1}"><p:cSld><p:spTree>{text}</p:spTree></p:cSld></p:sld>')

    def test_recall_short_principle_is_verified_in_actual_analysis_shape(self):
        q={'id':'q','material':'材料原文','prompt':'设问','task':'分析任务',
           'knowledgeRecall':{'id':'recall'},
           'answer':[{'principle':'答案原理','application':'答案应用'}],
           'analysis':[{'evidence':'材料原文','evidenceDisplay':'材料原文',
             'principle':'原理全句；补充','principleDisplay':'原理全句',
             'displayAnchors':{'material':['材料原文'],'knowledge':['原理全句']}}]}
        pages=[{'questionId':'q','page':1,'kind':'analysis','analysisBlocks':[
            {'analysisIndex':1,'materialShapeId':1,'knowledgeShapeId':2}]},
            {'questionId':'q','page':2,'kind':'answer'}]
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'q.pptx';self.write(path)
            self.assertTrue(check(path,{'questions':[q]},pages)['pass'])
            self.write(path,knowledge='知识已漏掉')
            self.assertTrue(any('compiled knowledge missing' in e for e in check(path,{'questions':[q]},pages)['errors']))
            self.write(path)
            self.assertTrue(any('missing analysis pages' in e for e in check(path,{'questions':[q]},pages[1:])['errors']))

    def test_hidden_question_is_not_delivered_for_normal_playback(self):
        raw={'id':'r','material':'材料原文','prompt':'设问'}
        registry={'sourceRecords':[raw],'questions':[{**raw,'id':'q','sourceRecords':['r']}]}
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'q.pptx';self.write(path,hidden=True)
            result=check_sources(path,registry,[{'questionId':'q','page':1}])
            self.assertFalse(result['pass']);self.assertTrue(any('hidden slides' in e for e in result['errors']))
