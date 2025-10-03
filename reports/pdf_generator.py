"""
HashInsight Enterprise - Professional PDF Generator
专业PDF生成器
"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import io
import logging
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)


class PDFGenerator:
    """PDF报告生成器"""
    
    def __init__(self, title: str = "Mining Profitability Report"):
        """初始化PDF生成器"""
        self.title = title
        self.buffer = io.BytesIO()
        self.doc = SimpleDocTemplate(
            self.buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        self.story = []
        self.styles = getSampleStyleSheet()
        
        # 自定义样式
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#0d6efd'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#212529'),
            spaceAfter=12
        ))
    
    def add_title(self):
        """添加标题"""
        title = Paragraph(self.title, self.styles['CustomTitle'])
        subtitle = Paragraph(
            f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            self.styles['Normal']
        )
        
        self.story.append(title)
        self.story.append(subtitle)
        self.story.append(Spacer(1, 0.5*inch))
    
    def add_summary(self, summary_data: Dict):
        """添加摘要部分"""
        heading = Paragraph("Executive Summary", self.styles['CustomHeading'])
        self.story.append(heading)
        
        for key, value in summary_data.items():
            text = f"<b>{key}:</b> {value}"
            p = Paragraph(text, self.styles['Normal'])
            self.story.append(p)
            self.story.append(Spacer(1, 0.1*inch))
        
        self.story.append(Spacer(1, 0.3*inch))
    
    def add_table(self, title: str, headers: List[str], data: List[List]):
        """添加数据表格"""
        heading = Paragraph(title, self.styles['CustomHeading'])
        self.story.append(heading)
        
        # 准备表格数据
        table_data = [headers] + data
        
        # 创建表格
        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d6efd')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        self.story.append(table)
        self.story.append(Spacer(1, 0.5*inch))
    
    def add_signature_placeholder(self):
        """添加电子签名占位符"""
        self.story.append(PageBreak())
        
        heading = Paragraph("Authorization & Signature", self.styles['CustomHeading'])
        self.story.append(heading)
        self.story.append(Spacer(1, 0.3*inch))
        
        signature_text = """
        <para>
        This report has been generated automatically by HashInsight Enterprise.<br/>
        <br/>
        Signature: _________________________<br/>
        <br/>
        Date: _________________________<br/>
        <br/>
        Name: _________________________<br/>
        </para>
        """
        
        p = Paragraph(signature_text, self.styles['Normal'])
        self.story.append(p)
    
    def export(self, filename: str = None) -> bytes:
        """导出PDF"""
        self.doc.build(self.story)
        
        if filename:
            with open(filename, 'wb') as f:
                f.write(self.buffer.getvalue())
            return None
        else:
            self.buffer.seek(0)
            return self.buffer.getvalue()
