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
import re

from . import email_report

# Emoji / pictographs / symbols / variation-selectors have no glyph in the PDF
# fonts (DejaVu etc.), so they render as blank/tofu boxes. The email keeps them
# (mail clients draw emoji natively); for the PDF we strip them. We deliberately
# do NOT touch ▲ ▼ (U+25B2/BC), · × – — which the report relies on and which the
# base fonts render fine.
_EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF"   # emoji & pictograph blocks
    "\u2300-\u23FF"            # technical (⏳ ⌛ ⏰ …)
    "\u2600-\u26FF"            # misc symbols (⚠ ☀ …)
    "\u2700-\u27BF"            # dingbats
    "\u2B00-\u2BFF"            # misc symbols & arrows (⭐ …)
    "\uFE00-\uFE0F"            # variation selectors
    "]+")


def _sanitize_for_pdf(html: str) -> str:
    # Keep the champions ranking meaningful once medals are gone.
    html = html.replace("\U0001F947", "1").replace("\U0001F948", "2").replace("\U0001F949", "3")
    # Drop any remaining emoji/symbols that the PDF fonts can't draw.
    return _EMOJI_RE.sub("", html)



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
    html = _sanitize_for_pdf(email_report.render_html(report, img_src, workspace))
    # Give the page sensible print margins; the email's own card styling is kept.
    page_css = CSS(string="@page { size: A4; margin: 9mm 7mm; }")
    HTML(string=html, base_url=os.path.dirname(os.path.abspath(out_path)) or ".").write_pdf(
        out_path, stylesheets=[page_css])
    return out_path
