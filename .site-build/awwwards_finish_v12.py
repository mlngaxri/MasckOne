from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'website/index.html'

s = INDEX.read_text()

START = '/* Awwwards art-direction finish v12 */'
END = '/* End Awwwards art-direction finish v12 */'
s = re.sub(re.escape(START) + r'.*?' + re.escape(END) + r'\n?', '', s, flags=re.S)

# Give the navigation an editorial index and a quiet development-status rail.
s = s.replace('data-view-target="object" aria-pressed="true" aria-current="page">Architecture</button>', 'data-view-target="object" data-index="01" aria-pressed="true" aria-current="page">Architecture</button>', 1)
s = s.replace('data-view-target="system" aria-pressed="false">Systems</button>', 'data-view-target="system" data-index="02" aria-pressed="false">Systems</button>', 1)
s = s.replace('data-view-target="proof" aria-pressed="false">Proof</button>', 'data-view-target="proof" data-index="03" aria-pressed="false">Proof</button>', 1)

if 'class="nav-status"' not in s:
    s = s.replace('</nav>\n<div class="nav-progress"', '</nav>\n<div class="nav-status" aria-hidden="true"><i></i><span>In development</span></div>\n<div class="nav-progress"', 1)

# Add an editorial pre-title without disturbing the hero mask or scroll choreography.
if 'class="hero-editorial-kicker"' not in s:
    s = s.replace('<div class="hero-copy" data-depth-copy>\n<h1>', '<div class="hero-copy" data-depth-copy>\n<div class="hero-editorial-kicker"><span>Facial cleansing</span><b>Engineering development</b></div>\n<h1>', 1)

# Proof pages get very quiet oversized chapter numerals in the background.
s = s.replace('<section class="page dark">', '<section class="page dark" data-page-no="01">', 1)
s = s.replace('<section class="page clay">', '<section class="page clay" data-page-no="02">', 1)

css = r'''
/* Awwwards art-direction finish v12 */
body{font-synthesis:none}

/* Navigation becomes a compact editorial instrument rather than a pill menu. */
.header{grid-template-columns:1fr auto 1fr}
.nav-status{
  justify-self:end;
  display:flex;
  align-items:center;
  gap:8px;
  padding-right:8px;
  font:400 7px/1 var(--mono);
  letter-spacing:.13em;
  text-transform:uppercase;
  color:rgba(24,33,28,.43);
  white-space:nowrap;
}
.nav-status i{
  width:5px;
  height:5px;
  border-radius:50%;
  background:#788970;
  box-shadow:0 0 0 0 rgba(120,137,112,.22);
  animation:statusPulse 3.6s ease-out infinite;
}
@keyframes statusPulse{0%,48%,100%{box-shadow:0 0 0 0 rgba(120,137,112,0)}62%{box-shadow:0 0 0 5px rgba(120,137,112,.10)}}
.nav button{display:flex;align-items:center;gap:7px}
.nav button::before{
  content:attr(data-index);
  font-size:5.5px;
  letter-spacing:.04em;
  opacity:.42;
  transform:translateY(-.5px);
  transition:opacity .28s var(--ease);
}
.nav button.active::before{opacity:.64}
.nav button::after{
  content:"";
  width:3px;
  height:3px;
  margin-left:-2px;
  border-radius:50%;
  background:currentColor;
  opacity:0;
  transform:scale(.4);
  transition:opacity .28s var(--ease),transform .28s var(--ease);
}
.nav button.active::after{opacity:.48;transform:scale(1)}

/* First-frame typography gets a designed reading order. */
.hero-editorial-kicker{
  display:flex;
  align-items:center;
  gap:11px;
  margin-bottom:19px;
  font:400 7px/1 var(--mono);
  letter-spacing:.14em;
  text-transform:uppercase;
  color:rgba(24,33,28,.48);
}
.hero-editorial-kicker::before{content:"";width:28px;height:1px;background:currentColor;opacity:.5}
.hero-editorial-kicker b{font-weight:400;color:rgba(24,33,28,.72)}
.hero h1 span{display:block;transform-origin:left bottom;animation:heroLineIn .92s var(--ease) both}
.hero h1 span:nth-child(2){font-style:italic;animation-delay:.07s}
.hero-editorial-kicker{animation:heroMetaIn .7s .04s var(--ease) both}
.hero-copy p{animation:heroMetaIn .78s .18s var(--ease) both}
.header{animation:headerIn .62s .03s ease-out both}
@keyframes heroLineIn{from{opacity:0;transform:translateY(.32em) skewY(1.3deg);filter:blur(4px)}to{opacity:1;transform:none;filter:none}}
@keyframes heroMetaIn{from{opacity:0;filter:blur(3px)}to{opacity:1;filter:none}}
@keyframes headerIn{from{opacity:0;filter:blur(6px)}to{opacity:1;filter:none}}

/* More tension between the serif display and technical support typography. */
.hero h1{letter-spacing:-.047em}
.hero h1 span:nth-child(2){letter-spacing:-.055em}
.handoff-caption b{letter-spacing:-.038em}
.page h2,.systems-copy h2{letter-spacing:-.047em}
.page-label,.systems-kicker{font-weight:400}

/* Proof receives a quiet chapter-scale background device instead of another card. */
.page[data-page-no]::before{
  content:attr(data-page-no);
  position:absolute;
  z-index:0;
  right:-.02em;
  top:50%;
  transform:translateY(-52%);
  font:400 clamp(210px,27vw,430px)/.72 var(--display);
  letter-spacing:-.075em;
  color:currentColor;
  opacity:.028;
  pointer-events:none;
}
.page.dark[data-page-no]::before{opacity:.045}
.page.clay[data-page-no]::before{opacity:.035}
.page-copy,.visual,.section-tag,.page-index,.evidence-line{position:relative}

/* Hairlines and technical UI use one consistent density. */
.detail-grid,.page-copy>p,.systems-copy p,.systems-facts{border-color:color-mix(in srgb,currentColor 16%,transparent)}
.page.dark .detail-grid,.page.dark .page-copy>p{border-color:rgba(255,255,255,.14)}
.section-tag{border-top-width:1px}
.systems-step{border-top-width:1px}
.evidence-line{max-width:560px}

/* Slightly more deliberate optical placement on large screens. */
@media(min-width:1181px){
  .hero-copy{left:max(var(--pad),5.2vw);top:14.8svh}
  .hero-clouds.hero-sky-orb{right:5.5vw}
  .handoff-caption{left:max(var(--pad),5.2vw)}
  .page{padding-left:max(var(--pad),5.2vw);padding-right:max(var(--pad),5.2vw)}
  .systems-copy{left:max(var(--pad),5.2vw)}
  .systems-copy-motion{left:auto;right:max(var(--pad),5.2vw)}
}

@media(max-width:900px){
  .nav-status{display:none}
  .header{grid-template-columns:auto 1fr;padding-left:13px}
  .nav{justify-self:end}
  .nav button{gap:5px;min-height:38px;padding-inline:9px}
  .nav button::before{font-size:5px}
  .nav button::after{display:none}
  .hero-editorial-kicker{margin-bottom:15px;font-size:6.5px;gap:9px}
  .hero-editorial-kicker::before{width:22px}
  .hero h1 span{animation-duration:.72s}
  .page[data-page-no]::before{right:-.04em;top:55%;font-size:46vw;opacity:.022}
  .page.dark[data-page-no]::before{opacity:.032}
}

@media(max-width:390px){
  .header{grid-template-columns:1fr;justify-items:center;padding-inline:5px}
  .nav{justify-self:center}
  .nav button{padding-inline:8px}
  .nav button::before{display:none}
  .hero-editorial-kicker{max-width:82vw;flex-wrap:wrap;row-gap:6px}
}

@media(max-width:900px) and (prefers-reduced-motion:reduce){
  .hero h1 span,.hero-editorial-kicker,.hero-copy p,.header,.nav-status i{animation:none!important}
}
/* End Awwwards art-direction finish v12 */
'''

s = s.replace('\n</style>\n</head>', '\n' + css + '\n</style>\n</head>', 1)

# Guard the product artwork and one-mask continuity while this pass changes only UI/art direction.
checks = [
    'mask-journey hero-mask-single',
    '<img class="hero-mask-art"',
    '/* Continuous approved product mask v10 */',
    '/* Awwwards editorial finish v11 */',
    '/* Awwwards art-direction finish v12 */',
    'class="hero-editorial-kicker"',
    'class="nav-status"',
    'data-index="01"',
    'data-index="02"',
    'data-index="03"',
    'data-page-no="01"',
    'data-page-no="02"',
]
for item in checks:
    if item not in s:
        raise RuntimeError(f'missing expected v12 element: {item}')
if 'masck-aperture-mask' in s or '<svg class="hero-mask-art"' in s:
    raise RuntimeError('mask artwork was altered by UI finish pass')
if s.count('mask-journey hero-mask-single') != 1:
    raise RuntimeError('single continuous mask invariant failed')

INDEX.write_text(s)
print('Awwwards art-direction finish v12 complete')
