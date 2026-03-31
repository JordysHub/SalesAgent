# src/utils/rfp/composer.py

"""
Proposal Composer — Pipeline Step 4

Assembles verified answers into a formatted DOCX proposal document.
Groups answers by category, renders each question-answer pair with source
citations, and marks flagged answers with a visible warning.

Currently uses a plain DOCX structure. Intended to be replaced with the
company DOCX template once available — only this file needs to change.
"""

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor


def compose_proposal(results: list[dict], rfp_source: str, output_path: str):
    doc = Document()

    # title
    title = doc.add_heading("Proposal Response", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    sub = doc.add_paragraph(f"In response to: {rfp_source}")
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_page_break()

    # group by category
    categories = {}
    for item in results:
        cat = item["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(item)

    for category, items in categories.items():
        doc.add_heading(category, level=1)

        for item in items:
            # question
            q_para = doc.add_paragraph()
            q_run = q_para.add_run(f"Q{item['id']}: {item['question']}")
            q_run.bold = True
            q_run.font.size = Pt(11)

            # answer
            answer_text = item["answer"]
            a_para = doc.add_paragraph(answer_text)
            a_para.style.font.size = Pt(11)

            # flags
            if not item.get("verified", True):
                flag = doc.add_paragraph()
                flag_run = flag.add_run(f"⚠ Flagged: {', '.join(item.get('issues', []))}")
                flag_run.font.color.rgb = RGBColor(0xFF, 0x00, 0x00)
                flag_run.font.size = Pt(9)

            # sources
            if item["sources"]:
                src_para = doc.add_paragraph()
                src_run = src_para.add_run(f"Sources: {', '.join(item['sources'])}")
                src_run.font.size = Pt(9)
                src_run.font.color.rgb = RGBColor(0x88, 0x88, 0x88)

            doc.add_paragraph()

    doc.save(output_path)
    print(f"[composer] Proposal saved to {output_path}")
