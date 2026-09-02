from pathlib import Path
from io import BytesIO
import base64

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'website/index.html'
ASSET = ROOT / 'website/images/masck-hero-mask-v2.webp'
CANDIDATE = ROOT / '.site-build/hero-mask-small-1.b64'
LOCAL_URL = 'https://raw.githubusercontent.com/mlngaxri/MasckOne/main/website/images/masck-hero-mask-v2.webp'
FALLBACK_URL = 'https://masck-one.vercel.app/images/masck-one-product-angle.webp'

s = INDEX.read_text()

# Decode and genuinely open the candidate. Header-only checks previously let a bad
# image through, so this pass uses Pillow and requires a real alpha channel.
use_local = False
try:
    from PIL import Image
    data = base64.b64decode(CANDIDATE.read_text().strip(), validate=True)
    with Image.open(BytesIO(data)) as probe:
        probe.load()
        im = probe.convert('RGBA')
    alpha = im.getchannel('A')
    if im.width < 300 or im.height < 300 or alpha.getextrema() != (0, 255):
        raise ValueError(f'unusable candidate {im.size}, alpha={alpha.getextrema()}')
    # Normalize the asset so every browser gets a conventional alpha WebP.
    if im.width > 700:
        h = round(im.height * 700 / im.width)
        im = im.resize((700, h), Image.Resampling.LANCZOS)
    im.save(ASSET, 'WEBP', quality=88, method=6, exact=True)
    with Image.open(ASSET) as check:
        check.load()
        if 'A' not in check.getbands():
            raise ValueError('normalized WebP lost alpha')
    use_local = True
    print('verified mask', im.size, ASSET.stat().st_size)
except Exception as exc:
    print('candidate rejected, using known-good hosted product render:', exc)

if not use_local:
    s = s.replace(LOCAL_URL, FALLBACK_URL)

# Mobile: the fixed journey now starts exactly where the static hero product sits.
s = s.replace(
    'const sx=innerWidth*(desktop()?.72:.67),sy0=innerHeight*(desktop()?.55:.56),cx=innerWidth*.5,cy=innerHeight*.52;',
    'const sx=innerWidth*(desktop()?.72:.67),sy0=innerHeight*(desktop()?.55:.54),cx=innerWidth*.5,cy=innerHeight*.52;',
    1,
)

# Do not let the static hero product drift independently on touch/mobile before
# the fixed journey crossfades in.
s = s.replace(
    "else if(el.classList.contains('hero-subject')){\nel.style.transform=`translate3d(${x+p*18}px,${y*.62}px,0) scale(${1+p*.018})`}",
    "else if(el.classList.contains('hero-subject')){\nif(desktop())el.style.transform=`translate3d(${x+p*18}px,${y*.62}px,0) scale(${1+p*.018})`;\nelse el.style.transform='translate3d(0,0,0)' }",
    1,
)

# Final mobile geometry. These values put the static product centre at ~67vw / 54vh,
# matching the journey start geometry above and keeping it inside the viewport.
mobile_css = r'''
/* Mobile stability repair */
@media(max-width:900px){
  .hero{min-height:100svh}
  .hero-mask-wrap.hero-subject{right:-8vw;top:31vh;width:82vw;max-width:none}
  .hero-mask-product{width:100%;transform:rotate(-4deg)}
  .mask-journey{width:82vw;max-width:480px}
  .mask-orbit-overlay{width:min(108vw,560px)}
  .mask-orbit-node span{font-size:clamp(28px,7.8vw,40px)}
  .handoff-halo{width:min(88vw,440px)}
}
'''
if '/* Mobile stability repair */' not in s:
    s = s.replace('\n</style>\n</head>', mobile_css + '\n</style>\n</head>', 1)

# Integrity assertions for the generated source.
if 'masck-hero-caucasian-mask-v1.webp' in s:
    raise RuntimeError('old portrait reference returned')
if 'updateHeaderVisibility();' in s:
    raise RuntimeError('stale navbar call returned')
if s.count('hero-mask-wrap hero-subject') != 1:
    raise RuntimeError('hero product wrapper count invalid')

INDEX.write_text(s)
print('mobile mask repair complete; local asset:', use_local)
