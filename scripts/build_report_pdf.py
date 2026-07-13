"""Convertit reports/RAPPORT.md en PDF via HTML + Chrome headless.

Usage : python scripts/build_report_pdf.py
Produit : reports/RAPPORT.html et reports/RAPPORT.pdf
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
MD = REPORTS / "RAPPORT.md"
HTML = REPORTS / "RAPPORT.html"
PDF = REPORTS / "RAPPORT.pdf"

CSS = """
@page { size: A4; margin: 18mm 16mm; }
* { box-sizing: border-box; }
body {
  font-family: -apple-system, "Helvetica Neue", Arial, sans-serif;
  font-size: 10.5pt; line-height: 1.55; color: #1e293b; max-width: 100%;
}
h1 { color: #6d28d9; font-size: 20pt; border-bottom: 3px solid #8B5CF6;
     padding-bottom: 8px; margin-top: 0; }
h2 { color: #7c3aed; font-size: 14pt; border-bottom: 1px solid #e2e8f0;
     padding-bottom: 4px; margin-top: 26px; page-break-after: avoid; }
h3 { color: #db2777; font-size: 11.5pt; margin-top: 18px; page-break-after: avoid; }
blockquote { border-left: 4px solid #8B5CF6; background: #f5f3ff; margin: 12px 0;
             padding: 8px 14px; color: #475569; border-radius: 4px; }
code { background: #f1f5f9; padding: 1px 5px; border-radius: 4px;
       font-family: "SF Mono", Menlo, monospace; font-size: 9pt; color: #db2777; }
pre { background: #0f172a; color: #e2e8f0; padding: 12px 14px; border-radius: 8px;
      overflow-x: auto; font-size: 8.5pt; line-height: 1.4; page-break-inside: avoid; }
pre code { background: none; color: #e2e8f0; padding: 0; }
table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 9pt;
        page-break-inside: avoid; }
th { background: #8B5CF6; color: #fff; padding: 6px 8px; text-align: left; }
td { border: 1px solid #e2e8f0; padding: 5px 8px; }
tr:nth-child(even) td { background: #f8fafc; }
img { max-width: 88%; display: block; margin: 14px auto; border: 1px solid #e2e8f0;
      border-radius: 8px; page-break-inside: avoid; }
a { color: #7c3aed; text-decoration: none; }
hr { border: none; border-top: 1px solid #e2e8f0; margin: 20px 0; }
ul, ol { padding-left: 22px; }
"""


def main() -> None:
    text = MD.read_text(encoding="utf-8")
    # Images en chemin absolu file:// pour que Chrome les charge
    text = text.replace("](figures/", f"]({(REPORTS / 'figures').as_uri()}/")
    body = markdown.markdown(
        text, extensions=["tables", "fenced_code", "toc", "sane_lists"]
    )
    html = (
        "<!DOCTYPE html><html lang='fr'><head><meta charset='utf-8'>"
        f"<style>{CSS}</style></head><body>{body}</body></html>"
    )
    HTML.write_text(html, encoding="utf-8")
    print(f"  HTML -> {HTML}")

    chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    subprocess.run(
        [chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
         f"--print-to-pdf={PDF}", HTML.as_uri()],
        check=True, capture_output=True,
    )
    print(f"  PDF  -> {PDF}")


if __name__ == "__main__":
    main()
