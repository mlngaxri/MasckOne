from pathlib import Path
import base64, hashlib

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

# Rebuild the approved product render from text-safe staged chunks.
mask_b64 = ''.join((ROOT / f'.site-build/product-mask-{i}.b64').read_text().strip() for i in (1, 2, 3))
mask_bytes = base64.b64decode(mask_b64)
if len(mask_bytes) != 48844 or mask_bytes[:4] != b'RIFF' or mask_bytes[8:12] != b'WEBP':
    raise RuntimeError(f'mask asset invalid: {len(mask_bytes)} bytes')
images = ROOT / 'website/images'
images.mkdir(parents=True, exist_ok=True)
(images / 'masck-hero-mask-v2.webp').write_bytes(mask_bytes)

mask_url = 'https://raw.githubusercontent.com/mlngaxri/MasckOne/main/website/images/masck-hero-mask-v2.webp'

s = once(
    s,
    '<img class="hero-clouds hero-bg" data-depth=".13" src="https://raw.githubusercontent.com/mlngaxri/MasckOne/main/website/images/masck-hero-sky-ribbons-v1.webp" alt="" fetchpriority="high" />',
    '<div class="hero-clouds hero-sky-orb" data-depth=".13" aria-hidden="true"></div>',
    'replace oversized sky image',
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
    'use same product for journey',
)

final_css = r'''
/* Final product-first hero */
.hero{background:linear-gradient(145deg,#f3eee6 0%,#edf1ed 50%,#dce8eb 100%)}
.hero-vignette{background:radial-gradient(circle at 70% 47%,rgba(255,255,255,.08) 0%,rgba(245,242,234,.03) 38%,rgba(233,240,241,.58) 100%)}
.hero-clouds.hero-sky-orb{inset:auto;right:8vw;top:13vh;width:clamp(350px,39vw,590px);height:auto;aspect-ratio:1;border-radius:50%;opacity:.88;z-index:1;background:radial-gradient(circle at 42% 36%,rgba(255,255,255,.98) 0 7%,rgba(255,255,255,.42) 18%,transparent 31%),radial-gradient(circle at 64% 66%,rgba(255,255,255,.92) 0 10%,rgba(255,255,255,.28) 25%,transparent 40%),radial-gradient(circle at 52% 48%,#8fc0df 0%,#a9cfe4 42%,#dcebf1 69%,rgba(232,241,242,0) 78%);filter:saturate(.82);-webkit-mask-image:radial-gradient(circle,#000 59%,rgba(0,0,0,.94) 66%,rgba(0,0,0,.42) 74%,transparent 82%);mask-image:radial-gradient(circle,#000 59%,rgba(0,0,0,.94) 66%,rgba(0,0,0,.42) 74%,transparent 82%);will-change:transform}
.hero-mask-wrap.hero-subject{position:absolute;z-index:5;right:6.5vw;top:12vh;bottom:auto;width:clamp(390px,42vw,620px);height:auto;filter:none;-webkit-mask-image:none;mask-image:none;will-change:transform,opacity}
.hero-mask-product{width:100%;height:auto;object-fit:contain;transform:rotate(-4deg);transform-origin:50% 50%;filter:drop-shadow(0 22px 30px rgba(24,33,28,.13)) drop-shadow(0 54px 72px rgba(24,33,28,.12))}
.mask-journey{width:clamp(390px,42vw,620px)}
.mask-journey img{filter:drop-shadow(0 22px 32px rgba(24,33,28,.14)) drop-shadow(0 52px 70px rgba(24,33,28,.10))}
@media(min-width:901px) and (max-width:1120px){.hero-mask-wrap.hero-subject{right:0;top:15vh;width:clamp(410px,49vw,560px)}.hero-clouds.hero-sky-orb{right:1vw;top:17vh;width:clamp(350px,45vw,510px)}}
@media(max-width:900px){.hero-clouds.hero-sky-orb{right:-14vw;top:25vh;width:82vw;height:auto;opacity:.78}.hero-mask-wrap.hero-subject{right:-17vw;top:30vh;bottom:auto;width:88vw;height:auto;-webkit-mask-image:none;mask-image:none}.hero-mask-product{transform:rotate(-4deg)}.mask-journey{width:88vw;max-width:500px}.hero-copy{z-index:10}.band.masck{z-index:3}.band.one{z-index:6}}
'''
s = once(s, '\n</style>\n</head>', final_css + '\n</style>\n</head>', 'append final hero css')

s = once(
    s,
    'const detach=smooth(clamp((sy-heroH*.18)/(heroH*.68),0,1));const show=smooth(clamp((sy-heroH*.22)/(heroH*.28),0,1));',
    'const detach=smooth(clamp((sy-heroH*.20)/(heroH*.66),0,1));const show=smooth(clamp((sy-heroH*.06)/(heroH*.16),0,1));',
    'retime product handoff',
)

old_geom = '''const sx=innerWidth*(desktop()?.735:.68),sy0=innerHeight*(desktop()?.46:.56),cx=innerWidth*.5,cy=innerHeight*.52;
const x=mix(sx,cx,detach),y=mix(sy0,cy,detach),scale=mix(desktop()?.58:.72,1,detach);
journey.style.opacity=String(show);journey.style.transform=`translate3d(${x}px,${y}px,0) translate(-50%,-50%) scale(${scale}) rotate(${mix(-5,0,detach)}deg)`;
if(heroSubject)heroSubject.style.opacity=String(1-smooth(clamp((sy-heroH*.6)/(heroH*.34),0,1))*.72);'''
new_geom = '''const sx=innerWidth*(desktop()?.72:.67),sy0=innerHeight*(desktop()?.55:.56),cx=innerWidth*.5,cy=innerHeight*.52;
const x=mix(sx,cx,detach),y=mix(sy0,cy,detach),scale=mix(1,desktop()?.72:.80,detach);
journey.style.opacity=String(show);journey.style.transform=`translate3d(${x}px,${y}px,0) translate(-50%,-50%) scale(${scale}) rotate(${mix(-4,0,detach)}deg)`;
if(heroSubject)heroSubject.style.opacity=String(1-show);'''
s = once(s, old_geom, new_geom, 'align product handoff')

# Navbar is permanently visible; remove the stale runtime call from the older reveal implementation.
s = s.replace('\nupdateHeaderVisibility();\nupdateNavProgress();', '\nupdateNavProgress();', 1)
if 'updateHeaderVisibility();' in s:
    raise RuntimeError('stale updateHeaderVisibility call remains')

if 'masck-hero-caucasian-mask-v1.webp' in s:
    raise RuntimeError('old model asset remains')
if 'masck-one-product-angle.webp' in s:
    raise RuntimeError('old journey product remains')
if 'masck-hero-sky-ribbons-v1.webp' in s:
    raise RuntimeError('old oversized sky asset remains')
if s.count(mask_url) != 2:
    raise RuntimeError('hero and journey do not share the same mask asset')

INDEX.write_text(s)
print('refined', blob_sha(INDEX.read_bytes()))
