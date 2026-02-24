"""
Export focus group sessions to CSV and PDF.

Both functions accept a session dict (shape from sessions.get_session()).
"""

from __future__ import annotations

import csv
import io

from fpdf import FPDF


def export_csv(session: dict) -> str:
    """
    Export a session as CSV text.

    Session metadata (question, sector, status) is included as comment headers.
    Columns: response_id, post_id, persona_summary, response_text, model.
    """
    buf = io.StringIO()

    # Metadata as comment header
    buf.write(f"# question: {session['question']}\n")
    buf.write(f"# sector: {session.get('sector') or 'all'}\n")
    buf.write(f"# status: {session['status']}\n")
    buf.write(f"# num_personas: {session['num_personas']}\n")
    buf.write(f"# created_at: {session['created_at']}\n")

    writer = csv.writer(buf)
    writer.writerow(["response_id", "post_id", "persona_summary", "response_text", "model"])

    for r in session.get("responses", []):
        writer.writerow([
            r["id"],
            r["post_id"],
            r["persona_summary"],
            r["response_text"],
            r["model"],
        ])

    return buf.getvalue()


def export_pdf(session: dict) -> bytes:
    """
    Export a session as a PDF document.

    Sections: title, question, metadata, then each persona response block.
    """
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Focus Group Session Report", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # Question
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Question:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 6, session["question"])
    pdf.ln(5)

    # Metadata
    pdf.set_font("Helvetica", "", 10)
    sector = session.get("sector") or "all"
    pdf.cell(0, 6, f"Sector: {sector}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Status: {session['status']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Personas: {session['num_personas']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Created: {session['created_at']}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    # Responses
    for i, r in enumerate(session.get("responses", []), 1):
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, f"Persona {i}: {r['persona_summary']}", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 5, r["response_text"])
        pdf.ln(5)

    return bytes(pdf.output())
