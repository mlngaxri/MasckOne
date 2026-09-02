from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'website/index.html'
s = INDEX.read_text()

# Idempotent cleanup of requested Object-page microcopy.
s = s.replace('<div class="hero-meta"><b>01</b>Object / 01 of 03<br>form in motion</div>\n', '')
s = s.replace('<div class="page-label">Physical architecture</div>\n', '')
s = s.replace('<div class="page-index">01 / Object / 03</div><div class="evidence-line">Fit, sealing, comfort and airway clearance remain physical evidence gates.</div>\n', '')

# Keep the existing 3px progress thickness, but physically clip it inside the pill border.
css = '''\n/* Object cleanup + navbar progress clipping */\n.header{overflow:hidden}\n.nav-progress{left:1px;right:1px;bottom:1px;height:3px;border-radius:0 0 999px 999px}\n'''
if '/* Object cleanup + navbar progress clipping */' not in s:
    s = s.replace('\n</style>', css + '\n</style>')

INDEX.write_text(s)
print('object cleanup applied')
