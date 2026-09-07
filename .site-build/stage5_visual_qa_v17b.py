from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "website/index.html"
MARKER = "/* Product inspection rendered QA v17b */"
V17 = "/* Product inspection and wearability v17 */"

s = INDEX.read_text(encoding="utf-8")

if MARKER in s:
    print("product inspection rendered QA v17b already applied")
    raise SystemExit(0)

if V17 not in s or s.count('class="product-inspection"') != 1:
    raise RuntimeError("prompt 17 product inspection is not in the expected generated state")

old = "  filter:drop-shadow(0 19px 29px rgba(24,33,28,.10)) drop-shadow(0 48px 64px rgba(24,33,28,.07));"
new = "  " + MARKER + "\n  filter:grayscale(.76) sepia(.10) saturate(.48) contrast(.96) brightness(1.035) drop-shadow(0 19px 29px rgba(24,33,28,.10)) drop-shadow(0 48px 64px rgba(24,33,28,.07));"

if s.count(old) != 1:
    raise RuntimeError(f"inspection filter contract changed: expected one match, got {s.count(old)}")

s = s.replace(old, new, 1)
INDEX.write_text(s, encoding="utf-8")
print("product inspection rendered QA v17b applied")
