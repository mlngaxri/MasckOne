from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "website" / "index.html"
MARKER = "<!-- Product use journey v18 -->"
RAW = "https://raw.githubusercontent.com/mlngaxri/MasckOne/main/website/"
ASSETS = (
    "images/masck-inspection-front-3q-v17c.webp",
    "images/masck-inspection-side-rear-v17c.webp",
    "images/masck-inspection-rear-3q-v17c.webp",
)

html = SITE.read_text(encoding="utf-8")
start = html.index(MARKER)
end = html.index("</section>", start) + len("</section>")
chapter = html[start:end]

before = chapter
for asset in ASSETS:
    chapter = chapter.replace(f'src="{asset}"', f'src="{RAW}{asset}"')

if chapter == before and any(f'src="{asset}"' in before for asset in ASSETS):
    raise RuntimeError("Prompt 18 asset URL repair made no progress")
for asset in ASSETS:
    if f'src="{asset}"' in chapter:
        raise RuntimeError(f"relative Prompt 18 product asset remained: {asset}")
    if f'src="{RAW}{asset}"' not in chapter:
        raise RuntimeError(f"absolute Prompt 18 product asset missing: {asset}")

SITE.write_text(html[:start] + chapter + html[end:], encoding="utf-8")
