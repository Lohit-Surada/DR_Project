"""
Diabetic Retinopathy AI Analysis — Medical PDF Report Generator
===============================================================
Produces a modern, multi-page A4 PDF using ReportLab Platypus.

Layout Structure:
-----------------
Page 1  : Title Banner + Patient Profile (key-value pairs, no table)
Page 2  : DR Classification (display confidence score + original fundus photograph)
Page 3  : Lesion Detection Results (YOLO26 counts table + annotated lesion image)
Page 4-5: Grad-CAM & Model Explainability (row-wise layout, images with titles underneath, point-wise insights)
Page 6  : Recovery & Prevention Priorities (recovery tips + urgent care guidance + medicines reference)

Header & Footer on Every Page:
- Header: "DR_CLASSIFICATION REPORT" top-right + subtle medical-blue divider
- Footer: "Date: DD MMM YYYY" bottom-left + "Page X of Y" bottom-right + subtle divider
"""

from __future__ import annotations

from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from classifier.guidance_service import (
    CURATED_RESPONSES,
    MEDICATION_REFERENCE,
    parse_response_to_components,
)

# ─── Color Palette ─────────────────────────────────────────────────────────────
NAVY       = colors.HexColor('#15345B')
BLUE       = colors.HexColor('#1677E8')
TEAL       = colors.HexColor('#0D9488')
TEXT_MAIN  = colors.HexColor('#172B4D')
TEXT_SEC   = colors.HexColor('#64748B')
BG_LIGHT   = colors.HexColor('#F8FAFC')
BG_CARD    = colors.HexColor('#F1F5F9')
BORDER_CLR = colors.HexColor('#E2E8F0')
WHITE      = colors.white

AMBER_BG   = colors.HexColor('#FFFBEB')
AMBER_BRD  = colors.HexColor('#FDE68A')
AMBER_TXT  = colors.HexColor('#92400E')

RED_BG     = colors.HexColor('#FEF2F2')
RED_BRD    = colors.HexColor('#FECACA')
RED_TXT    = colors.HexColor('#B91C1C')

GREEN_BG   = colors.HexColor('#F0FDF4')
GREEN_BRD  = colors.HexColor('#BBF7D0')
GREEN_TXT  = colors.HexColor('#15803D')

PAGE_W, PAGE_H = A4
MARGIN_LR  = 18 * mm
MARGIN_TOP = 25 * mm   # provides ample clearance beneath the header divider
MARGIN_BOT = 22 * mm   # provides ample clearance above the footer divider
CONTENT_W  = PAGE_W - 2 * MARGIN_LR  # 174 mm

HEADER_DIVIDER_Y = PAGE_H - 15 * mm
FOOTER_DIVIDER_Y = 14 * mm


# ─── Two-Pass Numbered Canvas ──────────────────────────────────────────────────
class _NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas that accumulates pages in the first pass and
    draws consistent headers and footers with accurate 'Page X of Y' on every page.
    """

    def __init__(self, *args, report_date: str = '', **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states: list[dict] = []
        self._report_date = report_date

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        page_count = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_header()
            self._draw_footer(page_count)
            super().showPage()
        super().save()

    def _draw_header(self):
        self.saveState()
        # Top right: "DR_CLASSIFICATION REPORT"
        self.setFont('Helvetica-Bold', 8)
        self.setFillColor(NAVY)
        self.drawRightString(PAGE_W - MARGIN_LR, PAGE_H - 12 * mm, 'DR_CLASSIFICATION REPORT')

        # Top left: subtle branding
        self.setFont('Helvetica', 8)
        self.setFillColor(TEXT_SEC)
        self.drawString(MARGIN_LR, PAGE_H - 12 * mm, 'RETINAIQ AI REPORT')

        # Subtle medical-blue horizontal divider
        self.setStrokeColor(BLUE)
        self.setLineWidth(1.0)
        self.line(MARGIN_LR, HEADER_DIVIDER_Y, PAGE_W - MARGIN_LR, HEADER_DIVIDER_Y)
        self.restoreState()

    def _draw_footer(self, page_count: int):
        self.saveState()
        # Subtle horizontal divider above footer
        self.setStrokeColor(BORDER_CLR)
        self.setLineWidth(0.5)
        self.line(MARGIN_LR, FOOTER_DIVIDER_Y, PAGE_W - MARGIN_LR, FOOTER_DIVIDER_Y)

        # Bottom left: "Date: DD MMM YYYY"
        self.setFont('Helvetica', 8)
        self.setFillColor(TEXT_SEC)
        self.drawString(MARGIN_LR, 8 * mm, f'Date: {self._report_date}')

        # Bottom right: 1, 2, 3...
        self.setFont('Helvetica', 8)
        self.setFillColor(TEXT_SEC)
        self.drawRightString(
            PAGE_W - MARGIN_LR, 8 * mm,
            f'{self._pageNumber}',
        )
        self.restoreState()


# ─── Style Sheet ───────────────────────────────────────────────────────────────
def _make_styles() -> dict:
    base = getSampleStyleSheet()
    return {
        'cover_title': ParagraphStyle(
            'CoverTitle',
            parent=base['Title'],
            fontSize=22,
            leading=26,
            alignment=TA_LEFT,
            textColor=NAVY,
            fontName='Helvetica',
            spaceAfter=2,
        ),
        'cover_sub': ParagraphStyle(
            'CoverSub',
            parent=base['Normal'],
            fontSize=13,
            leading=17,
            alignment=TA_LEFT,
            textColor=BLUE,
            fontName='Helvetica',
            spaceAfter=4,
        ),
        'cover_desc': ParagraphStyle(
            'CoverDesc',
            parent=base['Normal'],
            fontSize=9.5,
            leading=14,
            alignment=TA_LEFT,
            textColor=TEXT_SEC,
            spaceAfter=8,
        ),
        'section_num': ParagraphStyle(
            'SectionNum',
            parent=base['Normal'],
            fontSize=8.5,
            leading=11,
            textColor=BLUE,
            fontName='Helvetica-Bold',
            spaceBefore=4,
            spaceAfter=2,
        ),
        'section_head': ParagraphStyle(
            'SectionHead',
            parent=base['Heading2'],
            fontSize=15,
            leading=19,
            textColor=NAVY,
            fontName='Helvetica',
            spaceBefore=0,
            spaceAfter=4,
        ),
        'sub_head': ParagraphStyle(
            'SubHead',
            parent=base['Heading3'],
            fontSize=11,
            leading=15,
            textColor=NAVY,
            fontName='Helvetica',
            spaceBefore=8,
            spaceAfter=4,
        ),
        'body': ParagraphStyle(
            'Body',
            parent=base['BodyText'],
            fontSize=9.5,
            leading=14,
            textColor=TEXT_MAIN,
            spaceAfter=5,
        ),
        'body_sm': ParagraphStyle(
            'BodySm',
            parent=base['BodyText'],
            fontSize=9,
            leading=13,
            textColor=TEXT_MAIN,
            spaceAfter=4,
        ),
        'caption': ParagraphStyle(
            'Caption',
            parent=base['Normal'],
            fontSize=8,
            leading=11,
            textColor=TEXT_SEC,
            alignment=TA_CENTER,
            spaceBefore=3,
            spaceAfter=4,
        ),
        'profile_label': ParagraphStyle(
            'ProfileLabel',
            parent=base['Normal'],
            fontSize=8,
            leading=10,
            textColor=TEXT_SEC,
            fontName='Helvetica',
            spaceAfter=1,
        ),
        'profile_value': ParagraphStyle(
            'ProfileValue',
            parent=base['Normal'],
            fontSize=10,
            leading=14,
            textColor=TEXT_MAIN,
            fontName='Helvetica-Bold',
            spaceAfter=6,
        ),
        'kv_pair': ParagraphStyle(
            'KVPair',
            parent=base['Normal'],
            fontSize=10,
            leading=16,
            textColor=TEXT_MAIN,
            spaceAfter=5,
        ),
        'panel_title': ParagraphStyle(
            'PanelTitle',
            parent=base['Normal'],
            fontSize=8.5,
            leading=11,
            textColor=NAVY,
            fontName='Helvetica-Bold',
            spaceBefore=2,
            spaceAfter=2,
        ),
        'row_panel_title': ParagraphStyle(
            'RowPanelTitle',
            parent=base['Normal'],
            fontSize=9,
            leading=12,
            textColor=TEXT_SEC,
            fontName='Helvetica',
            alignment=TA_CENTER,
            spaceAfter=2,
        ),
        'row_panel_badge': ParagraphStyle(
            'RowPanelBadge',
            parent=base['Normal'],
            fontSize=7.5,
            leading=9.5,
            textColor=BLUE,
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
            spaceAfter=2,
        ),
        'row_panel_head': ParagraphStyle(
            'RowPanelHead',
            parent=base['Normal'],
            fontSize=8.5,
            leading=11,
            textColor=NAVY,
            fontName='Helvetica',
            spaceAfter=3,
        ),
        'row_panel_bullet': ParagraphStyle(
            'RowPanelBullet',
            parent=base['Normal'],
            fontSize=7.8,
            leading=11,
            textColor=TEXT_MAIN,
            spaceAfter=2.5,
        ),
        'panel_desc': ParagraphStyle(
            'PanelDesc',
            parent=base['Normal'],
            fontSize=7.5,
            leading=10.5,
            textColor=TEXT_SEC,
            spaceAfter=2,
        ),
        'disclaimer_box': ParagraphStyle(
            'DisclaimerBox',
            parent=base['BodyText'],
            fontSize=8.5,
            leading=12.5,
            textColor=AMBER_TXT,
            backColor=AMBER_BG,
            borderColor=AMBER_BRD,
            borderWidth=0.5,
            borderPadding=8,
            spaceAfter=4,
        ),
        'urgent_box': ParagraphStyle(
            'UrgentBox',
            parent=base['BodyText'],
            fontSize=8.5,
            leading=12.5,
            textColor=RED_TXT,
            backColor=RED_BG,
            borderColor=RED_BRD,
            borderWidth=0.5,
            borderPadding=8,
            spaceAfter=4,
        ),
        'success_box': ParagraphStyle(
            'SuccessBox',
            parent=base['BodyText'],
            fontSize=8.5,
            leading=12.5,
            textColor=GREEN_TXT,
            backColor=GREEN_BG,
            borderColor=GREEN_BRD,
            borderWidth=0.5,
            borderPadding=8,
            spaceAfter=4,
        ),
        'notice_box': ParagraphStyle(
            'NoticeBox',
            parent=base['BodyText'],
            fontSize=8.5,
            leading=12.5,
            textColor=TEXT_MAIN,
            backColor=BG_LIGHT,
            borderColor=BORDER_CLR,
            borderWidth=0.5,
            borderPadding=8,
            spaceAfter=4,
        ),
    }


# ─── Helper Builders ───────────────────────────────────────────────────────────
def _divider_flowable(color=BORDER_CLR, thickness=0.5, space_before=4, space_after=4) -> list:
    return [
        Spacer(1, space_before),
        HRFlowable(width='100%', thickness=thickness, color=color, spaceAfter=space_after),
    ]


def _section_heading(story: list, title: str, styles: dict) -> None:
    """Renders a clean section title without numbering or underline."""
    block = [
        Paragraph(title, styles['section_head']),
        Spacer(1, 2.5 * mm),
    ]
    story.append(KeepTogether(block))


def _shaded_table(rows: list[list], col_widths: list[float] | None = None) -> Table:
    """Clean two-column informational table with subtle shading."""
    if col_widths is None:
        col_widths = [55 * mm, CONTENT_W - 55 * mm]
    t = Table(rows, colWidths=col_widths, hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), BG_LIGHT),
        ('BACKGROUND', (1, 0), (1, -1), WHITE),
        ('GRID', (0, 0), (-1, -1), 0.4, BORDER_CLR),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), TEXT_SEC),
        ('TEXTCOLOR', (1, 0), (1, -1), TEXT_MAIN),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    return t


def _tip_table(rows: list[list]) -> Table:
    """Numbered tip table with teal accent numbering."""
    t = Table(rows, colWidths=[10 * mm, CONTENT_W - 10 * mm], hAlign='LEFT')
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (0, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), TEAL),
        ('FONTSIZE', (1, 0), (1, -1), 8.5),
        ('TEXTCOLOR', (1, 0), (1, -1), TEXT_MAIN),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [BG_LIGHT, WHITE]),
        ('GRID', (0, 0), (-1, -1), 0.3, BORDER_CLR),
    ]))
    return t


def _medicine_table(rows: list[list]) -> Table:
    t = Table(rows, colWidths=[55 * mm, CONTENT_W - 55 * mm], hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('TEXTCOLOR', (0, 1), (0, -1), TEXT_MAIN),
        ('TEXTCOLOR', (1, 1), (1, -1), TEXT_SEC),
        ('GRID', (0, 0), (-1, -1), 0.4, BORDER_CLR),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, BG_LIGHT]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 7),
        ('RIGHTPADDING', (0, 0), (-1, -1), 7),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    return t


# ─── Image Helper ──────────────────────────────────────────────────────────────
def _load_image(path: str, max_width: float, max_height: float, crop_title_bar: bool = False) -> Image | None:
    if not path:
        return None
    relative_path = urlparse(str(path)).path.replace('/media/', '').lstrip('/')
    full_path = Path(settings.MEDIA_ROOT) / relative_path
    if not full_path.is_file():
        return None
    try:
        with PILImage.open(full_path) as src:
            w, h = src.size
            if crop_title_bar and h > 100:
                # Crop the burned-in 48px black title bar from the top
                src_cropped = src.crop((0, 48, w, h))
                buf = BytesIO()
                src_cropped.save(buf, format='PNG')
                buf.seek(0)
                cw, ch = src_cropped.size
                scale = min(max_width / cw, max_height / ch, 1.0)
                return Image(buf, width=cw * scale, height=ch * scale)
        if w == 0 or h == 0:
            return None
        scale = min(max_width / w, max_height / h, 1.0)
        return Image(str(full_path), width=w * scale, height=h * scale)
    except Exception:
        return None


# ─── Main Medical Report Generator ─────────────────────────────────────────────
class MedicalReportGenerator:
    """Builds a multi-page clinical PDF report and returns raw bytes."""

    def __init__(self, report):
        self.report = report
        self.payload = report.payload or {}
        self.story: list = []
        self.styles = _make_styles()

    def _s(self, key: str) -> ParagraphStyle:
        return self.styles[key]

    def _p(self, text: str, style_key: str) -> Paragraph:
        return Paragraph(str(text), self._s(style_key))

    def _orig_image(self, max_width: float = CONTENT_W, max_height: float = 115 * mm) -> Image | None:
        orig_path = None
        try:
            orig_path = self.report.image.path
        except Exception:
            pass
        if not orig_path:
            return None
        try:
            with PILImage.open(orig_path) as src:
                w, h = src.size
            if w == 0 or h == 0:
                return None
            scale = min(max_width / w, max_height / h, 1.0)
            return Image(str(orig_path), width=w * scale, height=h * scale)
        except Exception:
            return None

    def _resolve_date(self) -> str:
        metadata = self.payload.get('metadata', {})
        if hasattr(self.report, 'created_at') and self.report.created_at:
            return self.report.created_at.strftime('%d %b %Y')
        if metadata.get('report_date'):
            return str(metadata['report_date'])
        if metadata.get('generated_at'):
            try:
                dt = datetime.fromisoformat(str(metadata['generated_at']).replace('Z', '+00:00'))
                return dt.strftime('%d %b %Y')
            except Exception:
                return str(metadata['generated_at'])[:10]
        return date.today().strftime('%d %b %Y')

    def _get_profile_field(self, key: str, profile: dict) -> str | None:
        aliases = {
            'full_name': ('full_name', 'fullName', 'name'),
            'age': ('age',),
            'sex': ('sex', 'gender'),
            'dob': ('dob', 'date_of_birth', 'dateOfBirth'),
            'email': ('email',),
            'contact_no': ('contact_no', 'phone', 'contactNo'),
            'address': ('address',),
            'blood_group': ('blood_group', 'bloodGroup'),
        }
        for alias in aliases.get(key, (key,)):
            val = profile.get(alias)
            if val is not None and str(val).strip():
                return str(val).strip()
        return None

    # ── Section 1: Page 1 — Title + Patient Profile (No Table) ─────────────────
    def _build_cover(self, report_date: str, profile: dict) -> None:
        s = self.story
        s.append(Spacer(1, 4 * mm))

        # Title banner - clean, non-repeating, no underline
        s.append(self._p('Diabetic Retinopathy AI Analysis Report', 'cover_title'))
        s.append(self._p('AI-Assisted Retinal Screening · RetinaIQ CNN + YOLO26 Pipeline', 'cover_desc'))
        s.append(Spacer(1, 5 * mm))

        # Examination Details Heading - clean, no section number or underline
        s.append(self._p('Examination Details', 'section_head'))
        s.append(Spacer(1, 3 * mm))

        # Build list of fields cleanly without a table
        FIELDS = [
            ('Report ID',            str(self.report.id)[:8].upper()),
            ('Report Date',          report_date),
            ('Patient Name',         self._get_profile_field('full_name', profile)),
            ('Age',                  self._get_profile_field('age', profile)),
            ('Sex',                  self._get_profile_field('sex', profile)),
            ('Date of Birth (DOB)',  self._get_profile_field('dob', profile)),
            ('Email',                self._get_profile_field('email', profile)),
            ('Contact No.',          self._get_profile_field('contact_no', profile)),
            ('Address',              self._get_profile_field('address', profile)),
            ('Blood Group',          self._get_profile_field('blood_group', profile)),
        ]

        # Render each field as two stacked lines: muted uppercase label, bold prominent value
        for label, val in FIELDS:
            if val:
                block = KeepTogether([
                    self._p(label.upper(), 'profile_label'),
                    self._p(str(val), 'profile_value'),
                ])
                s.append(block)

        s.append(Spacer(1, 4 * mm))

    # ── Section 2: Page 2 — DR Classification ─────────────────────────────────
    def _build_classification(self, classification: dict, report_date: str) -> None:
        s = self.story
        _section_heading(s, 'DR Classification', self.styles)

        s.append(self._p(
            'The following classification was generated by the RetinaIQ CNN severity model. '
            'This prediction represents an AI screening output and requires clinical interpretation.',
            'body_sm',
        ))
        s.append(Spacer(1, 2 * mm))

        title = classification.get('title') or classification.get('label') or 'Not available'
        severity = classification.get('severity') or classification.get('label') or 'Not available'

        # Primary display confidence matching web page DR classification score
        conf_val = (
            classification.get('confidence')
            or classification.get('model_confidence')
            or classification.get('actual_confidence')
            or classification.get('genuine_confidence')
        )
        if conf_val is not None:
            conf_display = f'{float(conf_val):.1f}%'
        else:
            conf_display = 'Not available'

        description = classification.get('description', '')

        rows = [
            ['Predicted Classification', title],
            ['Severity Stage',          severity],
            ['Model Confidence',        conf_display],
        ]
        if description:
            rows.append(['Clinical Note', description])

        s.append(KeepTogether([_shaded_table(rows)]))
        s.append(Spacer(1, 6 * mm))

        # Original fundus photograph
        orig = self._orig_image(max_height=115 * mm)
        if orig:
            s.append(KeepTogether([
                self._p('Original Fundus Image', 'sub_head'),
                orig,
                self._p(
                    'Fig 1 — Original digital retinal fundus photograph submitted for AI-assisted analysis.',
                    'caption',
                ),
            ]))

    # ── Section 3: Page 3 — Lesion Detection Results ──────────────────────────
    def _build_lesions(self, lesions: dict) -> None:
        s = self.story
        _section_heading(s, 'Lesion Detection Results', self.styles)

        s.append(self._p(
            'Detected by the YOLO26 deep object-detection architecture. Counts indicate localized '
            'bounding-box detections across the retinal image field.',
            'body_sm',
        ))
        s.append(Spacer(1, 2 * mm))

        summary = lesions.get('summary', {})
        LESION_LABELS = [
            ('0', 'Microaneurysm',
             'Focal outpouchings of capillary walls — earliest clinical sign of background DR.'),
            ('1', 'Haemorrhage',
             'Intraretinal bleeding indicating progressive capillary wall compromise.'),
            ('2', 'Hard Exudate',
             'Lipid and lipoprotein deposits resulting from chronic capillary hyperpermeability.'),
            ('3', 'Soft Exudate',
             'Cotton-wool spots reflecting focal ischaemic infarcts of retinal nerve fibres.'),
        ]

        rows = [['Lesion Type', 'Count', 'Clinical Significance']]
        for class_id, label, note in LESION_LABELS:
            count = summary.get(class_id, {}).get('count', 0)
            rows.append([label, str(count), note])
        rows.append(['Total Detections', str(lesions.get('total', 0)), ''])

        col_widths = [44 * mm, 18 * mm, CONTENT_W - 62 * mm]
        t = Table(rows, colWidths=col_widths, hAlign='LEFT')
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), NAVY),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8.5),
            ('TEXTCOLOR', (0, 1), (-1, -2), TEXT_MAIN),
            ('TEXTCOLOR', (1, 1), (1, -2), TEAL),
            ('FONTNAME', (1, 1), (1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.4, BORDER_CLR),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [WHITE, BG_LIGHT]),
            ('BACKGROUND', (0, -1), (-1, -1), BG_LIGHT),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 7),
            ('RIGHTPADDING', (0, 0), (-1, -1), 7),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        s.append(KeepTogether([t]))
        s.append(Spacer(1, 6 * mm))

        # Annotated lesion detection image
        lesion_img = _load_image(lesions.get('image_path', ''), max_width=CONTENT_W, max_height=115 * mm)
        if lesion_img:
            s.append(KeepTogether([
                self._p('Annotated Lesion Detection Map', 'sub_head'),
                lesion_img,
                self._p(
                    'Fig 2 — YOLO26-annotated fundus image with bounding boxes identifying detected lesion regions.',
                    'caption',
                ),
            ]))

    # ── Section 4: Page 4 & 5 — Grad-CAM & Model Explainability ───────────────
    def _build_gradcam(self, gradcam: dict) -> None:
        s = self.story
        _section_heading(s, 'Grad-CAM & Model Explainability', self.styles)

        s.append(self._p(
            'The visualizations below illustrate the internal spatial representations of the YOLO26 '
            'object-detection model. Each row displays the analytical image on the left with detailed '
            'clinical and model interpretation points on the right.',
            'body_sm',
        ))
        s.append(Spacer(1, 2.5 * mm))

        PANEL_ROWS_DATA = {
            'input': {
                'num': 'Fig 3a',
                'points': [
                    ('Primary Role', 'Unaltered color digital retinal fundus photograph submitted for diagnostic analysis.'),
                    ('Clinical Purpose', 'Provides the anatomical reference standard, depicting posterior pole vascular networks, optic disc, and foveal center.'),
                    ('Diagnostic Value', 'Ground truth baseline against which AI-generated heatmap activations and lesion detections are clinically verified.'),
                    ('Technical Spec', 'RGB Digital Fundus Capture · Standardized Preprocessing Entry Pipeline.'),
                ],
            },
            'gradcam': {
                'num': 'Fig 3b',
                'points': [
                    ('Primary Role', 'Gradient-weighted class activation map highlighting retinal regions exerting the highest neural weight.'),
                    ('Clinical Purpose', 'Backpropagates gradients from the detection head to layer-16 feature maps to reveal decision-critical lesion clusters.'),
                    ('Key Observations', 'Warm spectrum (red/yellow) marks focal pathological lesion clusters; cool colors denote background parenchymal regions.'),
                    ('Scope Clarification', 'Specific to YOLO26 lesion detection; does not independently explain the separate CNN severity classification.'),
                ],
            },
            'attention': {
                'num': 'Fig 3c',
                'points': [
                    ('Primary Role', 'Adaptive histogram equalization (CLAHE) local texture and contrast differential map.'),
                    ('Clinical Purpose', 'Amplifies microvascular contours to differentiate faint microaneurysms and haemorrhages from uneven retinal illumination.'),
                    ('Key Observations', 'Structural contrast enhancement (not Grad-CAM). Differentiates sharp lipid borders of hard exudates from cotton-wool spots.'),
                    ('Technical Spec', 'CLAHE Contrast Differential Filtering · Adaptive Local Histogram Clip.'),
                ],
            },
            'feature': {
                'num': 'Fig 3d',
                'points': [
                    ('Primary Role', 'Direct visual representation of deep intermediate activations extracted from the detection backbone.'),
                    ('Clinical Purpose', 'Demonstrates neural transformation of raw pixel intensities into composite spatial lesion features.'),
                    ('Key Observations', 'Validates that spatial coordinates of retinal abnormalities remain preserved before bounding-box regression heads.'),
                    ('Technical Spec', 'Intermediate Backbone Activations · Multi-Channel Spatial Tensor Projection.'),
                ],
            },
        }

        panels = gradcam.get('panels', [])
        combined_path = gradcam.get('combined_path', '') or gradcam.get('combined', '')

        # Build row tables
        row_tables = []
        for idx, panel in enumerate(panels):
            key = panel.get('key', '')
            data = PANEL_ROWS_DATA.get(key, {
                'num': f'Fig 3{chr(97 + idx)}',
                'points': [
                    ('Overview', panel.get('description', 'Model internal feature visualization.')),
                    ('Purpose', 'Provides visual insight into deep convolutional processing.'),
                    ('Analytical Review', 'Supplementary visual aid for ophthalmic research review.'),
                ],
            })

            p_img = _load_image(panel.get('image', ''), max_width=58 * mm, max_height=56 * mm, crop_title_bar=True)
            if not p_img:
                continue
            p_img.hAlign = 'CENTER'

            # Left column: image first, then Fig caption ONLY underneath (no title, no badge)
            left_flowables = [
                p_img,
                Spacer(1, 1.5 * mm),
                self._p(data['num'], 'row_panel_title'),
            ]

            # Right column: points-wise information (no bold tags on heading)
            right_flowables = [
                self._p('Clinical Information & Model Insights:', 'row_panel_head'),
                Spacer(1, 1.5 * mm),
            ]
            for label, text in data['points']:
                bullet_text = f'&#8226;&nbsp;&nbsp;<b>{label}:</b>&nbsp;{text}'
                right_flowables.append(self._p(bullet_text, 'row_panel_bullet'))

            col_widths = [64 * mm, CONTENT_W - 64 * mm]
            t_row = Table([[left_flowables, right_flowables]], colWidths=col_widths, hAlign='CENTER')
            t_row.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
                ('BOX', (0, 0), (-1, -1), 0.5, BORDER_CLR),
                ('INNERGRID', (0, 0), (-1, -1), 0.35, BORDER_CLR),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            row_tables.append(KeepTogether([t_row]))

        # Render rows across pages: 2 rows on Page 4, 2 rows on Page 5 (no repeated title on continuation)
        if len(row_tables) == 4:
            s.append(row_tables[0])
            s.append(Spacer(1, 3 * mm))
            s.append(row_tables[1])

            s.append(PageBreak())
            s.append(Spacer(1, 2 * mm))
            s.append(row_tables[2])
            s.append(Spacer(1, 3 * mm))
            s.append(row_tables[3])

        elif row_tables:
            for idx, r_tbl in enumerate(row_tables):
                if idx > 0 and idx % 2 == 0:
                    s.append(PageBreak())
                    s.append(Spacer(1, 2 * mm))
                s.append(r_tbl)
                s.append(Spacer(1, 3 * mm))

        elif combined_path:
            combined_img = _load_image(combined_path, max_width=CONTENT_W, max_height=80 * mm)
            if combined_img:
                s.append(KeepTogether([
                    self._p('Combined 4-Panel Visualization Strip', 'sub_head'),
                    combined_img,
                    self._p(
                        'Fig 3 — Four-panel explainability: input fundus, Grad-CAM saliency, '
                        'retinal attention map, and latent feature map.',
                        'caption',
                    ),
                ]))
        else:
            s.append(self._p('No explainability visual maps were generated for this analysis.', 'body_sm'))

    # ── Section 5: Page 6 — Recovery & Prevention Priorities ──────────────────
    def _build_recovery(self, guidance: dict, severity: str) -> None:
        s = self.story
        _section_heading(s, 'Recovery & Prevention Priorities', self.styles)

        s.append(self._p(
            'The following priorities provide educational guidance based on the AI screening result. '
            'This section does not constitute a clinical prescription or personalized treatment plan.',
            'body_sm',
        ))
        s.append(Spacer(1, 2.5 * mm))

        tips = [str(t).strip() for t in guidance.get('tips', []) if str(t).strip()]
        medications = guidance.get('medications', [])
        sev_str = str(severity).strip().lower()
        is_no_dr = sev_str in ('no dr', 'no diabetic retinopathy', 'no_dr')

        if is_no_dr:
            s.append(Paragraph(
                '<b>No DR-Specific Interventions Required:</b> Routine screening did not detect signs '
                'of diabetic retinopathy. Continue annual dilated eye examinations as advised by your '
                'eye-care provider and maintain optimal glycemic control.',
                self._s('success_box'),
            ))
        else:
            # If no tips in payload, supply evidence-based diabetic eye care priorities
            if not tips:
                tips = [
                    'Optimize glycemic and HbA1c control in consultation with your primary physician to decelerate retinal microvascular damage.',
                    'Maintain strict blood pressure (< 130/80 mmHg) and lipid targets to reduce hydrostatic strain on capillary walls.',
                    'Schedule a comprehensive clinical dilated exam and optical coherence tomography (OCT) with an ophthalmologist or retinal specialist.',
                    'Adopt an eye-healthy balanced diet rich in leafy greens and antioxidants, maintain regular physical activity, and abstain from smoking.',
                ]
            tip_rows = [[f'{i+1}.', tip] for i, tip in enumerate(tips[:4])]
            s.append(KeepTogether([_tip_table(tip_rows)]))

        s.append(Spacer(1, 4 * mm))

        # ── Urgent Eye Care Guidance
        s.append(Paragraph(
            '<b>Seek Urgent Eye Care Immediately:</b> If you experience sudden vision loss, '
            'a sudden shower of new floaters, flashes of light, a dark shadow or curtain '
            'across your field of vision, or severe eye pain, seek emergency ophthalmology care immediately.',
            self._s('urgent_box'),
        ))
        s.append(Spacer(1, 4 * mm))

        # ── Medicines & Clinical Discussion Guidance
        s.append(self._p('Medicines & Eye-Care Guidance', 'sub_head'))
        s.append(self._p(
            'The items listed below are educational references for discussion with your ophthalmologist — '
            'not prescriptions or treatment regimens. All therapeutic decisions must be determined '
            'by a licensed ophthalmologist following a comprehensive in-person clinical evaluation.',
            'body_sm',
        ))
        s.append(Spacer(1, 1.5 * mm))

        if is_no_dr or not medications:
            s.append(self._p(
                'No specific retinopathy medication is indicated at this stage based solely on the AI result. '
                'Medication and treatment decisions require an ophthalmologist\'s clinical assessment.',
                'body_sm',
            ))
        else:
            # Always derive medications from canonical curated responses matching the web page.
            # This ensures the report and web page show the exact same medicine cards regardless
            # of what was stored in the payload (Groq output may be garbled).
            canonical_meds = medications  # default to payload
            severity_key_map = {
                'mild': 'mild', 'mild npdr': 'mild', 'mild diabetic retinopathy': 'mild',
                'moderate': 'moderate', 'moderate npdr': 'moderate', 'moderate diabetic retinopathy': 'moderate',
                'severe': 'severe', 'severe npdr': 'severe', 'severe diabetic retinopathy': 'severe',
                'proliferative': 'proliferative', 'proliferative dr': 'proliferative',
                'proliferative diabetic retinopathy': 'proliferative',
            }
            sev_key = severity_key_map.get(sev_str)
            if sev_key and sev_key in CURATED_RESPONSES:
                _, curated_meds = parse_response_to_components(CURATED_RESPONSES[sev_key])
                if curated_meds:
                    canonical_meds = curated_meds
            # If still nothing usable, fall back to MEDICATION_REFERENCE
            if not canonical_meds:
                canonical_meds = MEDICATION_REFERENCE
            # Card-grid style matching the web page — up to 3 medicine cards in a row
            med_cards = []
            for med in canonical_meds[:3]:
                name = str(med.get('name', '')).strip()
                cat = str(med.get('category', '')).strip()
                if not name:
                    continue
                card_rows = [
                    [Paragraph(name, ParagraphStyle(
                        'MedName',
                        fontName='Helvetica-Bold',
                        fontSize=8.5,
                        leading=12,
                        textColor=TEXT_MAIN,
                    ))],
                    [Paragraph(cat, ParagraphStyle(
                        'MedCat',
                        fontName='Helvetica',
                        fontSize=7.5,
                        leading=10,
                        textColor=TEXT_SEC,
                        spaceBefore=2,
                    ))],
                ]
                card = Table(card_rows, colWidths=[54 * mm], hAlign='LEFT')
                card.setStyle(TableStyle([
                    ('BOX', (0, 0), (-1, -1), 0.4, BORDER_CLR),
                    ('BACKGROUND', (0, 0), (-1, -1), WHITE),
                    ('LEFTPADDING', (0, 0), (-1, -1), 7),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 7),
                    ('TOPPADDING', (0, 0), (-1, -1), 5),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ]))
                med_cards.append(card)

            if med_cards:
                # Pad to exactly 3 columns
                while len(med_cards) < 3:
                    empty = Table([['']], colWidths=[54 * mm])
                    empty.setStyle(TableStyle([('BOX', (0, 0), (-1, -1), 0, WHITE)]))
                    med_cards.append(empty)
                gap = (CONTENT_W - 3 * 54 * mm) / 2
                col_w = [54 * mm, gap, 54 * mm, gap, 54 * mm]
                grid_row = [med_cards[0], '', med_cards[1], '', med_cards[2]]
                grid = Table([grid_row], colWidths=col_w, hAlign='LEFT')
                grid.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 0),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                    ('TOPPADDING', (0, 0), (-1, -1), 0),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                ]))
                s.append(KeepTogether([grid]))

    # ── Public API ─────────────────────────────────────────────────────────────
    def build(self) -> bytes:
        metadata       = self.payload.get('metadata', {})
        classification = self.payload.get('classification', {})
        lesions        = self.payload.get('lesions', {})
        gradcam        = self.payload.get('gradcam', {})
        guidance       = self.payload.get('guidance') or {}
        profile        = metadata.get('profile') or {}

        report_date = self._resolve_date()

        # Page 1: Title Banner + Patient Profile (key-value pairs, no table)
        self._build_cover(report_date, profile)

        # Page 2: DR Classification + Original Fundus Photo
        self.story.append(PageBreak())
        self._build_classification(classification, report_date)

        # Page 3: Lesion Detection Results + Annotated Lesion Image
        self.story.append(PageBreak())
        self._build_lesions(lesions)

        # Page 4 & 5: Grad-CAM & Model Explainability (row-wise layout, titles under images)
        self.story.append(PageBreak())
        self._build_gradcam(gradcam)

        # Page 6: Recovery & Prevention Priorities
        self.story.append(PageBreak())
        severity = classification.get('severity', classification.get('label', ''))
        self._build_recovery(guidance, severity)

        # Render PDF
        output = BytesIO()
        doc = SimpleDocTemplate(
            output,
            pagesize=A4,
            rightMargin=MARGIN_LR,
            leftMargin=MARGIN_LR,
            topMargin=MARGIN_TOP,
            bottomMargin=MARGIN_BOT,
            title='Diabetic Retinopathy AI Analysis Report',
            author='RetinaIQ Clinical AI',
            subject='Diabetic Retinopathy AI-Assisted Screening Report',
        )

        def canvas_maker(*args, **kwargs):
            return _NumberedCanvas(*args, report_date=report_date, **kwargs)

        doc.build(self.story, canvasmaker=canvas_maker)
        return output.getvalue()