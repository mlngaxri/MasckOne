from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "website" / "index.html"

replacements = {
    ".j18m-action.prepare{left:9%;right:7%;top:43%": ".j18m-action.prepare{left:18%;right:18%;top:43%",
    ".j18m-action.choose span{position:absolute;left:28px;top:-5px;width:110px}": ".j18m-action.choose span{position:absolute;left:auto;right:28px;top:-5px;width:118px;text-align:right}",
    ".j18m-action.clean{left:7%;right:7%;top:24%": ".j18m-action.clean{left:18%;right:18%;top:24%",
    ".j18m-action.remove span{position:absolute;left:20px;top:15px;width:110px}": ".j18m-action.remove span{position:absolute;left:auto;right:20px;top:15px;width:120px;text-align:right}",
}

html = SITE.read_text(encoding="utf-8")
for old, new in replacements.items():
    count = html.count(old)
    if count != 1:
        raise RuntimeError(f"expected exactly one mobile annotation rule for {old!r}, found {count}")
    html = html.replace(old, new)

for old in replacements:
    if old in html:
        raise RuntimeError(f"stale mobile annotation rule remained: {old}")
for new in replacements.values():
    if new not in html:
        raise RuntimeError(f"repaired mobile annotation rule missing: {new}")

SITE.write_text(html, encoding="utf-8")
