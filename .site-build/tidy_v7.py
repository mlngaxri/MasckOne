from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'website/index.html'
ALPHA_SRC = 'https://raw.githubusercontent.com/mlngaxri/MasckOne/main/website/images/masck-hero-mask-v2.webp'
OPAQUE_SRC = 'https://masck-one.vercel.app/images/masck-one-product-angle.webp'

s = INDEX.read_text()

if s.count('mask-journey hero-mask-single') != 1:
    raise RuntimeError('expected exactly one continuous mask element')

# Preserve the approved product artwork exactly. The same single image element
# remains fixed and is transformed through the hero -> Architecture handoff;
# no SVG geometry is allowed to redraw or punch through the product silhouette.
product = f'''<div class="mask-journey hero-mask-single" role="img" aria-label="MASCK ONE product render">
<img class="hero-mask-art" src="{ALPHA_SRC}" alt="" fetchpriority="high" decoding="async" draggable="false" />
</div>'''

wrapper = re.compile(r'<div class="mask-journey hero-mask-single"[^>]*>.*?</div>', re.S)
s, n = wrapper.subn(product, s, count=1)
if n != 1:
    raise RuntimeError('continuous mask wrapper not found')

# Keep the critical product render warm in cache.
preload = f'<link rel="preload" as="image" href="{ALPHA_SRC}" />\n'
if preload not in s:
    s = s.replace('<style>\n', preload + '<style>\n', 1)

# Remove styling and markup from retired duplicate/static mask implementations.
for selector in [r'\.hero-mask-wrap\.hero-subject', r'\.hero-mask-product', r'\.hero-subject']:
    s = re.sub(selector + r'\{[^{}]*\}', '', s)

# No synthetic disc/glow should sit behind the product.
s = re.sub(r'\.mask-journey(?:::after|:after)\{[^{}]*\}', '', s)

css = r'''
/* Continuous approved product mask v10 */
.mask-journey.hero-mask-single{
  position:fixed;
  left:0;
  top:0;
  z-index:5;
  width:clamp(400px,40vw,590px);
  aspect-ratio:573/700;
  height:auto;
  display:grid;
  place-items:center;
  pointer-events:none;
  opacity:1;
  background:transparent!important;
  filter:none!important;
  transform:translate3d(-50%,-50%,0);
  transform-origin:50% 50%;
  will-change:transform;
  isolation:isolate;
}
.hero-mask-art{
  display:block;
  width:100%;
  height:100%;
  object-fit:contain;
  background:transparent!important;
  filter:drop-shadow(0 18px 26px rgba(24,33,28,.105)) drop-shadow(0 40px 54px rgba(24,33,28,.075));
  backface-visibility:hidden;
  -webkit-backface-visibility:hidden;
  transform:translateZ(0);
}
.mask-journey.hero-mask-single::before,
.mask-journey.hero-mask-single::after{
  content:none!important;
  display:none!important;
  background:none!important;
  filter:none!important;
}
@media(min-width:901px) and (max-width:1180px){
  .mask-journey.hero-mask-single{width:clamp(420px,47vw,550px)}
}
@media(max-width:900px){
  .mask-journey.hero-mask-single{width:67vw;max-width:none;will-change:transform}
  .hero-mask-art{filter:drop-shadow(0 14px 20px rgba(24,33,28,.095))}
}
@media(max-width:390px){
  .mask-journey.hero-mask-single{width:69vw}
}
'''

markers = [
    '/* Single physical mask continuity v6 */',
    '/* Continuous transparent product mask v7 */',
    '/* Continuous transparent product mask v8 */',
    '/* Continuous approved product mask v10 */',
]
starts = [s.find(m) for m in markers if s.find(m) != -1]
if starts:
    start = min(starts)
    end = s.find('</style>', start)
    if end == -1:
        raise RuntimeError('style close missing')
    s = s[:start] + css + '\n' + s[end:]
else:
    s = s.replace('\n</style>\n</head>', css + '\n</style>\n</head>', 1)

for dead in [
    'hero-mask-wrap hero-subject',
    'const heroSubject=',
    'heroSubject.style.opacity',
    'hero-mask-product',
    'masck-aperture-mask',
    'data-aperture=',
]:
    if dead in s:
        raise RuntimeError(f'dead/redrawn mask code remains: {dead}')
if s.count('mask-journey hero-mask-single') != 1:
    raise RuntimeError('single mask count changed')
if s.count('class="hero-mask-art"') != 1:
    raise RuntimeError('approved mask artwork must render exactly once')
if s.count(ALPHA_SRC) != 2:  # preload + image
    raise RuntimeError('approved alpha source should appear in preload and image only')
if OPAQUE_SRC in s:
    raise RuntimeError('opaque product-angle source remains')
if '/* Continuous approved product mask v10 */' not in s:
    raise RuntimeError('v10 mask CSS missing')

INDEX.write_text(s)
print('restored exact approved single-mask artwork v10')
