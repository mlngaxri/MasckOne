from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'website/index.html'
ALPHA_SRC = 'https://raw.githubusercontent.com/mlngaxri/MasckOne/main/website/images/masck-hero-mask-v2.webp'
OPAQUE_SRC = 'https://masck-one.vercel.app/images/masck-one-product-angle.webp'

s = INDEX.read_text()

if s.count('mask-journey hero-mask-single') != 1:
    raise RuntimeError('expected exactly one continuous mask element')

# The one moving product is rendered once through an inline SVG mask. The
# underlying WebP already carries alpha around the product and through the eye
# openings; the explicit aperture mask additionally guarantees the left eye,
# right eye and nose remain cut through even if the render is later replaced.
svg = f'''<div class="mask-journey hero-mask-single" role="img" aria-label="MASCK ONE product render">
<svg class="hero-mask-art" viewBox="0 0 573 700" aria-hidden="true" focusable="false">
<defs>
<mask id="masck-aperture-mask" x="0" y="0" width="573" height="700" maskUnits="userSpaceOnUse" maskContentUnits="userSpaceOnUse" style="mask-type:luminance">
<rect width="573" height="700" fill="white"/>
<ellipse data-aperture="left-eye" cx="286" cy="261" rx="80" ry="46" fill="black"/>
<path data-aperture="right-eye" d="M472 212 C462 217 459 229 462 240 C468 258 485 284 507 302 C510 304 512 305 514 304 C511 274 502 241 485 213 C481 209 476 209 472 212 Z" fill="black"/>
<path data-aperture="nose" d="M451.6 327.4 C439.2 331.3 431.8 339.3 428.2 345.8 L399.1 430.8 C400.0 448.0 399.8 455.3 402.0 460.3 C410.8 468.8 418.2 471.1 425.4 471.9 C441.0 472.0 456.6 471.0 465.9 469.5 C474.0 465.2 477.0 460.0 476.4 461.8 C482.0 452.0 484.0 444.0 484.0 443.9 C484.3 428.0 484.0 418.0 483.5 411.0 C481.0 393.0 478.0 376.0 475.0 366.1 C471.0 350.0 467.0 340.0 464.0 336.6 C459.0 331.0 455.0 328.0 451.6 327.4 Z" fill="black"/>
</mask>
</defs>
<image href="{ALPHA_SRC}" x="0" y="0" width="573" height="700" preserveAspectRatio="xMidYMid meet" mask="url(#masck-aperture-mask)"/>
</svg>
</div>'''

wrapper = re.compile(r'<div class="mask-journey hero-mask-single"[^>]*>.*?</div>', re.S)
s, n = wrapper.subn(svg, s, count=1)
if n != 1:
    raise RuntimeError('continuous mask wrapper not found')

# Preload the one critical product image since SVG <image> has no fetchpriority.
preload = f'<link rel="preload" as="image" href="{ALPHA_SRC}" />\n'
if preload not in s:
    s = s.replace('<style>\n', preload + '<style>\n', 1)

# Remove CSS belonging to the retired static hero/product copies.
for selector in [r'\.hero-mask-wrap\.hero-subject', r'\.hero-mask-product', r'\.hero-subject']:
    s = re.sub(selector + r'\{[^{}]*\}', '', s)

# Remove every legacy pseudo-glow behind the mask. Transparent apertures reveal
# the actual page behind the object rather than another product/glow layer.
s = re.sub(r'\.mask-journey(?:::after|:after)\{[^{}]*\}', '', s)

css = r'''
/* Continuous transparent product mask v8 */
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
  overflow:visible;
  background:transparent!important;
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
  .hero-mask-art{filter:drop-shadow(0 14px 20px rgba(24,33,28,.095))}
}
@media(max-width:390px){
  .mask-journey.hero-mask-single{width:69vw}
}
'''

# Replace whichever final continuity block is present rather than stacking fixes.
markers = ['/* Single physical mask continuity v6 */', '/* Continuous transparent product mask v7 */', '/* Continuous transparent product mask v8 */']
starts = [s.find(m) for m in markers if s.find(m) != -1]
if starts:
    start = min(starts)
    end = s.find('</style>', start)
    if end == -1:
        raise RuntimeError('style close missing')
    s = s[:start] + css + '\n' + s[end:]
else:
    s = s.replace('\n</style>\n</head>', css + '\n</style>\n</head>', 1)

for dead in ['hero-mask-wrap hero-subject', 'const heroSubject=', 'heroSubject.style.opacity', 'hero-mask-product']:
    if dead in s:
        raise RuntimeError(f'dead two-mask code remains: {dead}')
if s.count('mask-journey hero-mask-single') != 1:
    raise RuntimeError('single mask count changed')
if s.count(ALPHA_SRC) != 2:  # preload + SVG image
    raise RuntimeError('alpha mask source should appear in preload and SVG only')
if OPAQUE_SRC in s:
    raise RuntimeError('opaque product-angle source remains')
for aperture in ('left-eye', 'right-eye', 'nose'):
    if s.count(f'data-aperture="{aperture}"') != 1:
        raise RuntimeError(f'{aperture} aperture missing')
if s.count('id="masck-aperture-mask"') != 1:
    raise RuntimeError('SVG aperture mask id missing or duplicated')
if '/* Continuous transparent product mask v8 */' not in s:
    raise RuntimeError('v8 mask CSS missing')

INDEX.write_text(s)
print('tidy final single-mask v8 complete')
