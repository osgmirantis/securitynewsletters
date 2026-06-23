"""Render the newsletter as a PDF — identical content to the email body.

Reuses email_report.render_html (with charts inlined as base64 data URIs so the
PDF is self-contained) and converts it with WeasyPrint.

WeasyPrint needs a few system libraries at runtime (Pango/Cairo/GDK-PixBuf). On
Debian/Ubuntu CI runners:
    apt-get install -y libpango-1.0-0 libpangocairo-1.0-0 \\
                       libgdk-pixbuf-2.0-0 libffi-dev libcairo2
"""
from __future__ import annotations

import datetime as dt
import os

from . import email_report


def default_pdf_name(report: dict, workspace: str = "") -> str:
    def d(ts: int) -> str:
        return dt.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
    ws = (_slug(workspace) + "_") if workspace else ""
    return (f"Product-Security-Newsletter_{ws}"
            f"{d(report['window_start'])}_{d(report['generated_at'])}.pdf")


def _slug(s: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in s).strip("-") or "report"


def render_pdf(report: dict, charts: dict[str, str], out_path: str,
               workspace: str = "") -> str:
    """Write a PDF of the newsletter to out_path and return it."""
    try:
        from weasyprint import HTML, CSS
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "PDF export needs WeasyPrint (pip install weasyprint) plus its system "
            "libraries (Pango/Cairo/GDK-PixBuf)."
        ) from e

    img_src = {n: email_report.data_uri(p) for n, p in charts.items()}
    html = email_report.render_html(report, img_src, workspace)
    # Give the page sensible print margins; the email's own card styling is kept.
    page_css = CSS(string="@page { size: A4; margin: 9mm 7mm; }")
    HTML(string=html, base_url=os.path.dirname(os.path.abspath(out_path)) or ".").write_pdf(
        out_path, stylesheets=[page_css])
    return out_path
