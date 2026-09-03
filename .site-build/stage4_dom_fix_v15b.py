from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'website/index.html'
s = INDEX.read_text()

# Stage 4 removes the explanatory closing metadata (which previously contained
# the year). Re-introduce only the useful year marker immediately before the
# existing return action, independent of HTML attribute ordering.
if 'class="closing-year"' not in s:
    m = re.search(r'<button\b(?=[^>]*\bclass="closing-return")[^>]*>', s)
    if not m:
        raise RuntimeError('closing return action not found')
    s = s[:m.start()] + '<div class="closing-year" aria-hidden="true">2026</div>\n' + s[m.start():]

assert s.count('class="closing-year"') == 1
assert s.count('class="closing-return"') == 1
INDEX.write_text(s)
print('stage 4 DOM fix v15b complete')
