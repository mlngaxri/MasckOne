from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'website/index.html'
ALPHA_SRC = 'https://raw.githubusercontent.com/mlngaxri/MasckOne/main/website/images/masck-hero-mask-v2.webp'
OPAQUE_SRC = 'https://masck-one.vercel.app/images/masck-one-product-angle.webp'

s = INDEX.read_text()

if s.count('mask-journey hero-mask-single') != 1:
    raise RuntimeError('expected exactly one continuous mask element')

# Point the one continuous mask at the repository alpha asset.
pattern = r'(<div class="mask-journey hero-mask-single"[^>]*><img src=")[^"]+("[^>]*></div>)'
s, n = re.subn(pattern, lambda m: m.group(1) + ALPHA_SRC + m.group(2), s, count=1)
if n != 1:
    raise RuntimeError('continuous mask image markup not found')

# Give the image stable intrinsic dimensions without changing its visual sizing.
s = s.replace(
    'alt="" fetchpriority="high" decoding="async" />',
    'alt="" fetchpriority="high" decoding="async" draggable="false" />',
    1,
)

# Remove CSS belonging to the retired static hero copy.
for selector in [r'\.hero-mask-wrap\.hero-subject', r'\.hero-mask-product', r'\.hero-subject']:
    s = re.sub(selector + r'\{[^{}]*\}', '', s)

# Remove every legacy pseudo-glow behind the mask. Transparent apertures must
# reveal the real page behind the product, never a synthetic disc/glow layer.
s = re.sub(r'\.mask-journey(?:::after|:after)\{[^{}]*\}', '', s)

css = r'''
/* Continuous transparent product mask v7 */
.mask-journey.hero-mask-single{
  position:fixed;
  left:0;
  top:0;
  z-index:5;
  width:clamp(400px,40vw,590px);
  aspect-ratio:1122/1402;
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
.mask-journey.hero-mask-single img{
  display:block;
  width:100%;
  height:100%;
  object-fit:contain;
  background:transparent!important;
  mix-blend-mode:normal!important;
  filter:drop-shadow(0 18px 26px rgba(24,33,28,.105)) drop-shadow(0 40px 54px rgba(24,33,28,.075));
  backface-visibility:hidden;
  -webkit-backface-visibility:hidden;
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
  .mask-journey.hero-mask-single img{filter:drop-shadow(0 14px 20px rgba(24,33,28,.095))}
}
@media(max-width:390px){
  .mask-journey.hero-mask-single{width:69vw}
}
'''

# v6 is the final style block. Replace it rather than stacking another override.
start = s.find('/* Single physical mask continuity v6 */')
if start != -1:
    end = s.find('</style>', start)
    if end == -1:
        raise RuntimeError('style close missing')
    s = s[:start] + css + '\n' + s[end:]
elif '/* Continuous transparent product mask v7 */' not in s:
    s = s.replace('\n</style>\n</head>', css + '\n</style>\n</head>', 1)

for dead in ['hero-mask-wrap hero-subject', 'const heroSubject=', 'heroSubject.style.opacity', 'hero-mask-product']:
    if dead in s:
        raise RuntimeError(f'dead two-mask code remains: {dead}')
if s.count('mask-journey hero-mask-single') != 1:
    raise RuntimeError('single mask count changed')
if s.count(ALPHA_SRC) != 1:
    raise RuntimeError('alpha mask source must appear exactly once')
if OPAQUE_SRC in s:
    raise RuntimeError('opaque product-angle source remains')
if '/* Continuous transparent product mask v7 */' not in s:
    raise RuntimeError('v7 mask CSS missing')

INDEX.write_text(s)
print('tidy final single-mask v7 complete')
