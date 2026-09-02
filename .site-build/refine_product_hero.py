from pathlib import Path
import base64, hashlib, re

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'website/index.html'
EXPECTED = 'e9b9925b88bcccf1a564413615dd8aa1354468db'


def blob_sha(data: bytes) -> str:
    h = hashlib.sha1()
    h.update(f'blob {len(data)}\0'.encode())
    h.update(data)
    return h.hexdigest()


def once(s: str, old: str, new: str, label: str) -> str:
    n = s.count(old)
    if n != 1:
        raise RuntimeError(f'{label}: expected 1 match, got {n}')
    return s.replace(old, new, 1)

raw = INDEX.read_bytes()
sha = blob_sha(raw)
if sha != EXPECTED:
    raise RuntimeError(f'unexpected website baseline {sha}')
s = raw.decode()

# Rebuild generated assets from staged text chunks.
mask_b64 = ''.join((ROOT / f'.site-build/product-mask-{i}.b64').read_text().strip() for i in (1,2,3))
sky_b64 = ''.join((ROOT / f'.site-build/product-sky-{i}.b64').read_text().strip() for i in (1,2))
mask_bytes = base64.b64decode(mask_b64)
sky_bytes = base64.b64decode(sky_b64)
if len(mask_bytes) != 75284 or mask_bytes[:4] != b'RIFF' or mask_bytes[8:12] != b'WEBP':
    raise RuntimeError(f'mask asset invalid: {len(mask_bytes)} bytes')
if len(sky_bytes) != 71508 or sky_bytes[:4] != b'RIFF' or sky_bytes[8:12] != b'WEBP':
    raise RuntimeError(f'sky asset invalid: {len(sky_bytes)} bytes')
images = ROOT / 'website/images'
images.mkdir(parents=True, exist_ok=True)
(images / 'masck-hero-mask-v2.webp').write_bytes(mask_bytes)
(images / 'masck-hero-sky-portal-v2.webp').write_bytes(sky_bytes)

mask_url = 'https://raw.githubusercontent.com/mlngaxri/MasckOne/main/website/images/masck-hero-mask-v2.webp'
sky_url = 'https://raw.githubusercontent.com/mlngaxri/MasckOne/main/website/images/masck-hero-sky-portal-v2.webp'

s = once(
    s,
    '<img class="hero-clouds hero-bg" data-depth=".13" src="https://raw.githubusercontent.com/mlngaxri/MasckOne/main/website/images/masck-hero-sky-ribbons-v1.webp" alt="" fetchpriority="high" />',
    f'<img class="hero-clouds hero-sky-portal" data-depth=".13" src="{sky_url}" alt="" fetchpriority="high" />',
    'replace hero sky layer',
)

s = once(
    s,
    '<img class="hero-person hero-subject" data-depth=".52" src="https://raw.githubusercontent.com/mlngaxri/MasckOne/main/website/images/masck-hero-caucasian-mask-v1.webp" alt="Woman looking upward while wearing a MASCK ONE concept render" fetchpriority="high" />',
    f'<div class="hero-mask-wrap hero-subject" data-depth=".52"><img class="hero-mask-product" src="{mask_url}" alt="MASCK ONE product render" fetchpriority="high" /></div>',
    'replace model with product',
)

s = once(
    s,
    '<div class="mask-journey" aria-hidden="true"><img src="https://masck-one.vercel.app/images/masck-one-product-angle.webp" alt="" /></div>',
    f'<div class="mask-journey" aria-hidden="true"><img src="{mask_url}" alt="" /></div>',
    'use same mask for journey',
)

final_css = r'''
/* Final product-first hero */
.hero{background:linear-gradient(145deg,#f3eee6 0%,#edf1ed 48%,#dce9ed 100%)}
.hero-vignette{background:radial-gradient(circle at 70% 48%,rgba(255,255,255,.10) 0%,rgba(241,238,229,.05) 34%,rgba(234,241,243,.62) 100%)}
.hero-clouds.hero-sky-portal{inset:auto;left:auto;right:8vw;top:12vh;width:clamp(370px,40vw,610px);height:auto;opacity:.82;object-fit:contain;filter:saturate(.82) brightness(1.04);z-index:1;will-change:transform}
.hero-mask-wrap.hero-subject{position:absolute;z-index:5;right:4.5vw;top:50%;bottom:auto;width:clamp(410px,45vw,700px);height:auto;filter:none;-webkit-mask-image:none;mask-image:none;will-change:transform,opacity}
.hero-mask-product{width:100%;height:auto;object-fit:contain;transform:rotate(-4deg);transform-origin:50% 50%;filter:drop-shadow(0 24px 30px rgba(24,33,28,.12)) drop-shadow(0 58px 74px rgba(24,33,28,.13))}
.mask-journey{width:clamp(410px,45vw,700px)}
.mask-journey img{filter:drop-shadow(0 24px 34px rgba(24,33,28,.14)) drop-shadow(0 54px 72px rgba(24,33,28,.10))}
@media(min-width:901px) and (max-width:1120px){.hero-mask-wrap.hero-subject{right:-1vw;top:51%;width:clamp(430px,52vw,610px)}.hero-clouds.hero-sky-portal{right:2vw;top:15vh;width:clamp(360px,47vw,540px)}}
@media(max-width:900px){.hero-clouds.hero-sky-portal{right:-15vw;top:23vh;width:84vw;height:auto;opacity:.78}.hero-mask-wrap.hero-subject{right:-18vw;top:54%;bottom:auto;width:86vw;height:auto;-webkit-mask-image:none;mask-image:none}.hero-mask-product{transform:rotate(-4deg)}.mask-journey{width:86vw;max-width:520px}.hero-copy{z-index:10}.band.masck{z-index:3}.band.one{z-index:6}}
'''
s = once(s, '\n</style>\n</head>', final_css + '\n</style>\n</head>', 'append final hero css')

s = once(
    s,
    'const detach=smooth(clamp((sy-heroH*.18)/(heroH*.68),0,1));const show=smooth(clamp((sy-heroH*.22)/(heroH*.28),0,1));',
    'const detach=smooth(clamp((sy-heroH*.20)/(heroH*.68),0,1));const show=smooth(clamp((sy-heroH*.10)/(heroH*.18),0,1));',
    'retime mask handoff',
)

old_geom = '''const sx=innerWidth*(desktop()?.735:.68),sy0=innerHeight*(desktop()?.46:.56),cx=innerWidth*.5,cy=innerHeight*.52;
const x=mix(sx,cx,detach),y=mix(sy0,cy,detach),scale=mix(desktop()?.58:.72,1,detach);
journey.style.opacity=String(show);journey.style.transform=`translate3d(${x}px,${y}px,0) translate(-50%,-50%) scale(${scale}) rotate(${mix(-5,0,detach)}deg)`;
if(heroSubject)heroSubject.style.opacity=String(1-smooth(clamp((sy-heroH*.6)/(heroH*.34),0,1))*.72);'''
new_geom = '''const sx=innerWidth*(desktop()?.705:.65),sy0=innerHeight*(desktop()?.50:.54),cx=innerWidth*.5,cy=innerHeight*.52;
const x=mix(sx,cx,detach),y=mix(sy0,cy,detach),scale=mix(1,desktop()?.72:.80,detach);
journey.style.opacity=String(show);journey.style.transform=`translate3d(${x}px,${y}px,0) translate(-50%,-50%) scale(${scale}) rotate(${mix(-4,0,detach)}deg)`;
if(heroSubject)heroSubject.style.opacity=String(1-show);'''
s = once(s, old_geom, new_geom, 'align product handoff')

# The navbar is permanently visible now; this stale call was left behind by a prior refinement.
s = s.replace('\nupdateHeaderVisibility();\nupdateNavProgress();', '\nupdateNavProgress();', 1)
if 'updateHeaderVisibility();' in s:
    raise RuntimeError('stale updateHeaderVisibility call remains')

if 'masck-hero-caucasian-mask-v1.webp' in s:
    raise RuntimeError('old model asset remains')
if 'masck-one-product-angle.webp' in s:
    raise RuntimeError('old journey mask remains')
if mask_url not in s or sky_url not in s:
    raise RuntimeError('new hero assets missing from HTML')

INDEX.write_text(s)
print('refined', blob_sha(INDEX.read_bytes()))
