from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.pdfgen import canvas


class _NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        page_count = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_footer(page_count)
            super().showPage()
        super().save()

    def _draw_footer(self, page_count):
        self.saveState()
        self.setFont('Helvetica', 8)
        self.setFillColor(colors.HexColor('#64748b'))
        self.drawString(18 * mm, 10 * mm, 'Diabetic Retinopathy AI Analysis')
        self.drawRightString(A4[0] - 18 * mm, 10 * mm, f'Page {self._pageNumber} of {page_count}')
        self.restoreState()


class MedicalReportGenerator:
    def __init__(self, report):
        self.report = report
        self.payload = report.payload
        self.story = []
        styles = getSampleStyleSheet()
        self.title_style = ParagraphStyle('ReportTitle', parent=styles['Title'], alignment=TA_CENTER, textColor=colors.HexColor('#0c4a6e'), spaceAfter=8)
        self.section_style = ParagraphStyle('ReportSection', parent=styles['Heading2'], textColor=colors.HexColor('#075985'), spaceBefore=8, spaceAfter=8)
        self.body_style = ParagraphStyle('ReportBody', parent=styles['BodyText'], leading=15, spaceAfter=6)
        self.small_style = ParagraphStyle('ReportSmall', parent=styles['BodyText'], fontSize=8, textColor=colors.HexColor('#64748b'), leading=10)
        self.disclaimer_style = ParagraphStyle('ReportDisclaimer', parent=self.body_style, textColor=colors.HexColor('#92400e'), backColor=colors.HexColor('#fffbeb'), borderColor=colors.HexColor('#fcd34d'), borderWidth=0.5, borderPadding=8)

    def _image(self, path, max_width=175 * mm, max_height=105 * mm):
        if not path:
            return None
        relative_path = urlparse(str(path)).path.replace('/media/', '').lstrip('/')
        full_path = Path(settings.MEDIA_ROOT) / relative_path
        if not full_path.is_file():
            return None
        with PILImage.open(full_path) as source:
            width, height = source.size
        scale = min(max_width / width, max_height / height)
        return Image(str(full_path), width=width * scale, height=height * scale)

    def _table(self, rows):
        table = Table(rows, colWidths=[60 * mm, 110 * mm], hAlign='LEFT')
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e0f2fe')),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#cbd5e1')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('PADDING', (0, 0), (-1, -1), 7),
        ]))
        return table

    def build(self):
        metadata = self.payload.get('metadata', {})
        classification = self.payload.get('classification', {})
        lesions = self.payload.get('lesions', {})
        profile = metadata.get('profile') or {}
        profile_labels = [
            ('full_name', 'Full name'),
            ('email', 'Email'),
            ('phone', 'Phone'),
            ('date_of_birth', 'Date of birth'),
        ]
        profile_rows = [['User profile', 'Value']]
        for key, label in profile_labels:
            value = profile.get(key)
            if value is not None and str(value).strip():
                profile_rows.append([label, str(value)])

        self.story.extend([
            Paragraph('DIABETIC RETINOPATHY<br/>AI ANALYSIS REPORT', self.title_style),
            Paragraph('AI-Assisted Retinal Image Analysis', self.body_style),
        ])
        if len(profile_rows) > 1:
            self.story.extend([
                Paragraph('USER PROFILE', self.section_style),
                self._table(profile_rows),
                Spacer(1, 10),
            ])
        self.story.append(Paragraph('ORIGINAL FUNDUS IMAGE', self.section_style))
        original = self._image(self.report.image.name, max_height=90 * mm)
        if original:
            self.story.append(original)
        self.story.extend([
            Spacer(1, 8),
            Paragraph('OVERALL ANALYSIS', self.section_style),
            self._table([
                ['DR Classification', str(classification.get('title', 'Not available'))],
                ['Confidence', f"{classification.get('confidence', 'Not available')}%"],
                ['Severity', str(classification.get('severity', 'Not available'))],
            ]),
            PageBreak(),
            Paragraph('1. DR CLASSIFICATION', self.section_style),
            Paragraph('This is an AI-generated classification result and not a confirmed medical diagnosis.', self.body_style),
            self._table([
                ['Classification', str(classification.get('title', 'Not available'))],
                ['Confidence', f"{classification.get('confidence', 'Not available')}%"],
                ['Severity', str(classification.get('severity', 'Not available'))],
            ]),
            PageBreak(),
            Paragraph('2. LESION DETECTION', self.section_style),
            Paragraph('The YOLO model detected the following visual patterns in the submitted image.', self.body_style),
        ])
        summary = lesions.get('summary', {})
        rows = [['Lesion type', 'Detected count']]
        for class_id, label in [('0', 'Microaneurysm'), ('1', 'Haemorrhage'), ('2', 'Hard Exudate'), ('3', 'Soft Exudate')]:
            rows.append([label, str(summary.get(class_id, {}).get('count', 0))])
        rows.append(['Total detections', str(lesions.get('total', 0))])
        self.story.append(self._table(rows))
        lesion_image = self._image(lesions.get('image_path', ''), max_height=110 * mm)
        if lesion_image:
            self.story.extend([Spacer(1, 10), lesion_image])
        self.story.extend([
            PageBreak(),
            Paragraph('3. GRAD-CAM & MODEL EXPLAINABILITY', self.section_style),
            Paragraph('The Grad-CAM visualization uses gradients and feature activations from the YOLO26 model to highlight regions that contributed to the selected model prediction.', self.body_style),
            Paragraph('The Retinal Attention Map is an image-processing visualization based on contrast enhancement and local image differences. This visualization is not Grad-CAM.', self.body_style),
            Paragraph('The YOLO26 Feature Visualization represents internal model feature representations generated through the Ultralytics visualization pipeline.', self.body_style),
        ])
        combined = self._image(self.payload.get('gradcam', {}).get('combined_path', ''), max_height=70 * mm)
        if combined:
            self.story.append(combined)
        panels = self.payload.get('gradcam', {}).get('panels', [])
        if panels:
            self.story.append(Spacer(1, 10))
            for panel in panels:
                panel_image = self._image(panel.get('image', ''), max_height=52 * mm)
                if panel_image:
                    self.story.extend([Paragraph(str(panel.get('title', 'Visualization')), self.body_style), panel_image, Spacer(1, 6)])

        guidance = self.payload.get('guidance') or {}
        guidance_tips = [str(tip).strip() for tip in guidance.get('tips', []) if str(tip).strip()][:3]
        medication_rows = [['Medicine reference', 'Category']]
        for medication in guidance.get('medications', [])[:3]:
            name = str(medication.get('name', '')).strip()
            category = str(medication.get('category', '')).strip()
            if name and category:
                medication_rows.append([name, category])
        self.story.extend([PageBreak(), Paragraph('4. RECOVERY & PREVENTION GUIDANCE', self.section_style)])
        if guidance_tips:
            self.story.append(Paragraph('Three concise educational priorities based on the AI-assisted classification:', self.body_style))
            self.story.append(self._table([[f'{index}.', tip] for index, tip in enumerate(guidance_tips, 1)]))
        else:
            self.story.append(Paragraph('No recovery guidance is required for this classification. Continue routine eye examinations and general prevention care.', self.body_style))
        if len(medication_rows) > 1:
            self.story.extend([
                Spacer(1, 10),
                Paragraph('Medicine names for clinician discussion', self.body_style),
                self._table(medication_rows),
                Paragraph('These are reference names only, not prescriptions. Treatment decisions must be made by a qualified clinician.', self.small_style),
            ])
        self.story.extend([
            Spacer(1, 12),
            Paragraph('SAFETY NOTE', self.section_style),
            Paragraph('AI-generated analysis is educational and does not diagnose, prescribe, or confirm a cure. Seek urgent eye care for sudden vision loss, severe eye pain, or major new flashes and floaters.', self.disclaimer_style),
        ])
        output = BytesIO()
        document = SimpleDocTemplate(output, pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=18 * mm, bottomMargin=18 * mm, title='Diabetic Retinopathy AI Analysis Report')
        document.build(self.story, canvasmaker=_NumberedCanvas)
        return output.getvalue()