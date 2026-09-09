"""Produce a human-readable deletion log, never insert deleted content into DOCs."""
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from fonts import resolve_fonts

def build(model,path,title):
    if not model.get('removed_questions'):return None
    pdfmetrics.registerFont(TTFont('WorksheetReportSong',resolve_fonts()['font_file'],subfontIndex=0))
    font='WorksheetReportSong';style=ParagraphStyle('body',fontName=font,fontSize=10,leading=15,wordWrap='CJK')
    P=lambda s:Paragraph(escape(str(s)).replace('\n','<br/>'),style)
    story=[Paragraph('浙江选考题删除记录',ParagraphStyle('title',parent=style,fontSize=18,leading=25)),Spacer(1,10),P(title),Spacer(1,6),P('原文件：'+Path(model['source']).name),Spacer(1,10)]
    cs=sum(r['type']=='choice' for r in model['removed_questions']);ws=len(model['removed_questions'])-cs
    story += [P(f'删除选择题{cs}道；综合题留空{ws}道。两版同步处理。'),Spacer(1,12)]
    rows=[[P('原题号／题源'),P('原题摘要'),P('处理方式')]]
    for r in model['removed_questions']:
        rows.append([P(str(r['source_number'])+'（'+('选择题' if r['type']=='choice' else '综合题')+'）\n'+r['source_label']),P(r['stem_excerpt'][:105]+'…'),P('整题删除，后续保留题号前移。' if r['type']=='choice' else f"删除题干、材料及答案；保留原第{r['source_number']}题空位，待人工粘贴新题。")])
    tab=Table(rows,colWidths=[125,240,142],repeatRows=1)
    tab.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E5EDF5')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F6F8FA')]),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
    story += [tab,Spacer(1,15),P('保留题目编号对照（原号 → 输出号）'),Spacer(1,5),P('；'.join(f"{x['source_number']} → {x['output_number']}"+('（空位）' if x['placeholder'] else '') for x in model['number_mapping'])),Spacer(1,12),P('复核说明：浙江地区的模拟考、联考及其他省份高考不因本规则删除。综合题空位按原题号保留，可能出现编号空缺；不自动补题，不沿用被删综合题的分值。此表是程序操作记录，供人工复核。')]
    def footer(c,d):
        c.setFont(font,8);c.drawString(44,25,'删除记录 · '+Path(model['source']).stem[:28]);c.drawRightString(A4[0]-44,25,str(d.page))
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    SimpleDocTemplate(str(path),pagesize=A4,leftMargin=44,rightMargin=44,topMargin=40,bottomMargin=45,title=title+' 删除记录').build(story,onFirstPage=footer,onLaterPages=footer)
    return path
