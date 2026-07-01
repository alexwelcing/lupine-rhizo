#!/usr/bin/env python3
"""Build a PDF of the confident 3x3x3 paper from Markdown using Chrome headless."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import markdown


CSS = """
@page { size: letter; margin: 2.5cm; }
body {
    font-family: "Times New Roman", Georgia, serif;
    font-size: 11pt;
    line-height: 1.5;
    color: #111;
    max-width: 18cm;
    margin: 0 auto;
}
h1 { font-size: 16pt; text-align: center; margin-bottom: 0.3em; }
h2 { font-size: 13pt; margin-top: 1.4em; margin-bottom: 0.4em; border-bottom: 1px solid #ccc; }
h3 { font-size: 11pt; margin-top: 1.1em; margin-bottom: 0.3em; }
p { margin: 0.6em 0; text-align: justify; }
table {
    border-collapse: collapse;
    margin: 1em auto;
    font-size: 10pt;
    width: 100%;
}
th, td { border: 1px solid #999; padding: 4px 6px; text-align: right; }
th { background: #f2f2f2; text-align: center; }
img { max-width: 100%; display: block; margin: 1em auto; }
code { font-family: Consolas, Monaco, monospace; font-size: 9pt; background: #f5f5f5; padding: 1px 3px; }
blockquote { border-left: 3px solid #ccc; margin-left: 0; padding-left: 1em; color: #333; }
sup { font-size: 0.75em; }
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="lupine-layer2-3x3x3-confident.md", help="Markdown input")
    parser.add_argument("--output", default="lupine-layer2-3x3x3-confident.pdf", help="PDF output")
    args = parser.parse_args()

    here = Path(__file__).resolve().parent
    md_path = here / args.input
    pdf_path = here / args.output
    html_path = pdf_path.with_suffix(".html")

    if not md_path.exists():
        print(f"Input not found: {md_path}", file=sys.stderr)
        return 1

    md_text = md_path.read_text(encoding="utf-8")
    body = markdown.markdown(md_text, extensions=["tables"])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>A Sub-Core-Hour 3×3×3 Elastic-Constant Reference for MatPES Foundation MLIPs</title>
<style>
{CSS}
</style>
</head>
<body>
{body}
</body>
</html>
"""
    html_path.write_text(html, encoding="utf-8")

    chrome_cmd = [
        "google-chrome",
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--run-all-compositor-stages-before-draw",
        "--print-to-pdf-no-header",
        f"--print-to-pdf={pdf_path}",
        f"file://{html_path}",
    ]
    print("Running:", " ".join(chrome_cmd))
    subprocess.run(chrome_cmd, check=True)
    print(f"Wrote PDF: {pdf_path}")
    print(f"Wrote HTML: {html_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
