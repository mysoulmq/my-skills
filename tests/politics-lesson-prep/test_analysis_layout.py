import sys, unittest
from pathlib import Path
from xml.etree import ElementTree as E
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'skills/politics-lesson-prep/scripts'))
from analysis_presentation import fit_analysis_pages,normalize_heading_dashes

class LayoutTests(unittest.TestCase):
    def fit(self, measure, **kw):
        args=dict(base_font=18,min_font=16,recall_top=160,
                  recall_reserved_height=125,content_bottom=535)
        args.update(kw)
        return fit_analysis_pages([1,2],measure,**args)
    def measure(self, ids, font):
        return {'recallHeight':35,'groups':[{'index':i,'bodyHeight':font*7,
                'knowledgeHeight':font*5} for i in ids]}
    def test_bounded_reduction_fits_pairs_and_keeps_knowledge_space(self):
        pages=self.fit(self.measure)
        self.assertEqual(len(pages),1)
        self.assertEqual(pages[0]['fontPt'],16)
        self.assertEqual(pages[0]['indices'],[1,2])
        self.assertEqual(pages[0]['recallHeight'],125)
        self.assertEqual(pages[0]['analysisTop'],297)
    def test_no_reduction_without_page_benefit(self):
        pages=self.fit(self.measure,content_bottom=700)
        self.assertEqual(pages[0]['fontPt'],18)
    def test_long_recall_and_groups_measured_jointly(self):
        def m(ids,font):
            d=self.measure(ids,font);d['recallHeight']=180 if len(ids)>1 else 100
            return d
        pages=self.fit(m)
        self.assertEqual([p['indices'] for p in pages],[[1],[2]])
        self.assertTrue(all(p['fontPt']==18 for p in pages))
    def test_no_fit_fails_instead_of_eating_recall(self):
        with self.assertRaisesRegex(ValueError,'No readable'):
            self.fit(self.measure,content_bottom=320)
    def test_unbounded_shrink_rejected(self):
        with self.assertRaises(ValueError):self.fit(self.measure,min_font=10)
    def test_source_order_must_survive(self):
        def m(ids,font):
            d=self.measure(ids,font);d['groups'].reverse();return d
        with self.assertRaisesRegex(ValueError,'order'):self.fit(m)
    def test_dashes_remain_native_and_preserve_other_heading_text(self):
        a='http://schemas.openxmlformats.org/drawingml/2006/main';n='{'+a+'}'
        for label in ('审题--','审材料— —','审材料——'):
            root=E.fromstring(f'<shape xmlns:a="{a}"><a:p><a:pPr algn="l"/><a:r><a:rPr b="1" sz="2400"><a:ea typeface="楷体"/></a:rPr><a:t>{label}</a:t></a:r><a:endParaRPr/></a:p><a:p><a:r><a:t>对应原理方法论</a:t></a:r></a:p></shape>')
            self.assertEqual(normalize_heading_dashes(root),1)
            p=root.find(n+'p');runs=p.findall(n+'r')
            self.assertEqual(runs[1].find(n+'t').text,'——')
            self.assertEqual(runs[1].find(n+'rPr').get('spc'),'0')
            self.assertEqual(runs[0].find(n+'rPr/'+n+'ea').get('typeface'),'楷体')
            self.assertEqual(p[-1].tag,n+'endParaRPr')
            self.assertEqual(root[-1].find('.//'+n+'t').text,'对应原理方法论')
            self.assertEqual(normalize_heading_dashes(root),1)
