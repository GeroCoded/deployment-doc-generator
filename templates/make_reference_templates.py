"""Generates the three *reference* templates with placeholder markup.

These are NOT meant to ship as-is — they show you exactly what Jinja/docxtpl
markup to paste into your real company-branded Technical Summary / Code
Comparison / Change Request files. Run once; then mirror the placeholders into
your branded copies.
"""
import os

from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

HERE = os.path.dirname(os.path.abspath(__file__))


def _add_toc(doc, heading_levels="1-1"):
    """Insert a Word TOC field (index). Word fills it on open / field update."""
    p = doc.add_paragraph()
    run = p.add_run()
    for char_type, instr in (("begin", None), (None, f' TOC \\o "{heading_levels}" \\h \\z \\u '),
                             ("separate", None)):
        el = OxmlElement("w:fldChar") if char_type else OxmlElement("w:instrText")
        if char_type:
            el.set(qn("w:fldCharType"), char_type)
        else:
            el.set(qn("xml:space"), "preserve")
            el.text = instr
        run._r.append(el)
    placeholder = p.add_run("Right-click → Update Field to build the index.")
    placeholder.italic = True
    end = p.add_run()
    end_el = OxmlElement("w:fldChar")
    end_el.set(qn("w:fldCharType"), "end")
    end._r.append(end_el)


def _force_update_fields(doc):
    settings = doc.settings.element
    upd = OxmlElement("w:updateFields")
    upd.set(qn("w:val"), "true")
    settings.append(upd)


def make_technical_summary():
    doc = Document()
    doc.add_paragraph("Technical Summary - {{ ticket_ids }}", style="Title")
    doc.add_paragraph("Change Request {{ cr_number }} — {{ deploy_date }}", style="Subtitle")
    doc.add_paragraph("Index", style="Heading 1")
    _add_toc(doc, "1-1")
    doc.add_page_break()

    doc.add_paragraph("{%p for t in tickets %}")
    doc.add_paragraph("{{ t.id }}: {{ t.title }}", style="Heading 1")
    for n, (q, field) in enumerate([
        ("What is the problem?", "t.problem"),
        ("How does this affect the users?", "t.user_impact"),
        ("Solution Implemented", "t.solution"),
        ("How was this tested?", "t.testing"),
    ], start=1):
        doc.add_paragraph(f"{n}) {q}", style="Heading 2")
        doc.add_paragraph("{{ %s }}" % field)
    doc.add_paragraph("{%p endfor %}")

    _force_update_fields(doc)
    doc.save(os.path.join(HERE, "technical_summary_template.docx"))


def make_code_comparison():
    doc = Document()
    doc.add_paragraph("Code Comparison - {{ ticket_ids }}", style="Title")

    doc.add_paragraph("{%p for repo in repos %}")
    doc.add_paragraph("{{ repo.name }}", style="Heading 1")
    doc.add_paragraph("Version to be deployed: {{r repo.deploy_link }}", style="List Bullet")
    doc.add_paragraph("Current PROD version: {{r repo.prod_link }}", style="List Bullet")
    doc.add_paragraph("Comparison Link: {{r repo.compare_link }}", style="List Bullet")
    doc.add_paragraph("Files changed", style="Heading 2")
    doc.add_paragraph("{{ repo.stat }}")
    doc.add_paragraph("Commits", style="Heading 2")
    doc.add_paragraph("{{r repo.commits_rich }}")
    doc.add_paragraph("Code changes", style="Heading 2")
    doc.add_paragraph("{{r repo.diff_rich }}")
    doc.add_paragraph("{%p endfor %}")

    doc.save(os.path.join(HERE, "code_comparison_template.docx"))


def make_change_request():
    wb = Workbook()
    ws = wb.active
    ws.title = "Change Request"
    ws.column_dimensions["A"].width = 42
    ws.column_dimensions["B"].width = 80

    header_fill = PatternFill("solid", fgColor="D9E1F2")
    ws["A1"] = "Field"
    ws["B1"] = "Value"
    for c in ("A1", "B1"):
        ws[c].font = Font(bold=True)
        ws[c].fill = header_fill

    rows = [
        ("Change Request Number", "{{ cr_number }}"),
        ("Deployment Date", "{{ deploy_date }}"),
        ("Tickets", "{{ ticket_ids }}"),
        ("Repositories Touched", "{{ repo_names }}"),
        ("Versions to be Deployed", "{{ deploy_versions }}"),
        ("Backout Versions", "{{ backout_versions }}"),
        ("Business Justification", "{{ business_justification }}"),
        ("Summary of Change", "{{ change_summary }}"),
        ("What happens if the change is NOT deployed?", "{{ impact_if_not_deployed }}"),
        ("Worst case if deployed and something goes wrong?", "{{ worst_case }}"),
        ("Rollback / Backout Plan", "{{ rollback_plan }}"),
        ("Deployment Steps", "{{ deployment_steps | lines }}"),
    ]
    for i, (q, a) in enumerate(rows, start=2):
        ws.cell(row=i, column=1, value=q).font = Font(bold=True)
        cell = ws.cell(row=i, column=2, value=a)
        cell.alignment = Alignment(wrap_text=True, vertical="top")

    wb.save(os.path.join(HERE, "change_request_template.xlsx"))


if __name__ == "__main__":
    make_technical_summary()
    make_code_comparison()
    make_change_request()
    print("Reference templates written to", HERE)
