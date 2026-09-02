from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'website/index.html'
LOCAL_URL = 'https://raw.githubusercontent.com/mlngaxri/MasckOne/main/website/images/masck-hero-mask-v2.webp'
FALLBACK_URL = 'https://masck-one.vercel.app/images/masck-one-product-angle.webp'

s = INDEX.read_text()

# The generated repo WebP is not trusted on the live hero. Use the known-good
# hosted product render for both the static hero and the moving handoff so there
# can never be an image swap or broken decode between the two states.
s = s.replace(LOCAL_URL, FALLBACK_URL)

old_mobile = '''/* Mobile stability repair */
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
new_mobile = '''/* Mobile stability repair */
@media(max-width:900px){
  .hero{min-height:100svh}
  .hero-clouds.hero-sky-orb{right:-3vw;top:26vh;width:70vw;height:auto;opacity:.72}
  .hero-mask-wrap.hero-subject{right:-4vw;top:33vh;width:74vw;max-width:none;will-change:opacity}
  .hero-mask-product{width:100%;transform:rotate(-4deg);filter:drop-shadow(0 16px 24px rgba(24,33,28,.12)) drop-shadow(0 34px 48px rgba(24,33,28,.10))}
  .mask-journey{width:74vw;max-width:400px;will-change:transform,opacity}
  .mask-orbit-overlay{width:min(96vw,500px)}
  .mask-orbit-node span{font-size:clamp(25px,7vw,36px)}
  .handoff-halo{width:min(86vw,420px)}
}
'''
if old_mobile in s:
    s = s.replace(old_mobile, new_mobile, 1)
elif new_mobile not in s:
    s = s.replace('\n</style>\n</head>', '\n' + new_mobile + '\n</style>\n</head>', 1)

# On mobile the moving product used to appear almost immediately, creating two
# independent copies of the mask. Delay that crossfade until late in the hero.
old_timing = 'const detach=smooth(clamp((sy-heroH*.20)/(heroH*.66),0,1));const show=smooth(clamp((sy-heroH*.06)/(heroH*.16),0,1));'
new_timing = '''const isDesktop=desktop();
const detach=isDesktop?smooth(clamp((sy-heroH*.20)/(heroH*.66),0,1)):smooth(clamp((sy-heroH*.60)/(heroH*.32),0,1));
const show=isDesktop?smooth(clamp((sy-heroH*.06)/(heroH*.16),0,1)):smooth(clamp((sy-heroH*.58)/(heroH*.12),0,1));'''
if old_timing in s:
    s = s.replace(old_timing, new_timing, 1)

old_geom = 'const sx=innerWidth*(desktop()?.72:.67),sy0=innerHeight*(desktop()?.55:.54),cx=innerWidth*.5,cy=innerHeight*.52;\nconst x=mix(sx,cx,detach),y=mix(sy0,cy,detach),scale=mix(1,desktop()?.72:.80,detach);'
new_geom = 'const sx=innerWidth*(isDesktop?.72:.67),sy0=innerHeight*(isDesktop?.55:.54),cx=innerWidth*.5,cy=innerHeight*.52;\nconst x=mix(sx,cx,detach),y=mix(sy0,cy,detach),scale=mix(1,isDesktop?.72:.82,detach);'
if old_geom in s:
    s = s.replace(old_geom, new_geom, 1)

# Static hero product stays fixed on mobile; only the fixed journey moves.
old_subject = "else if(el.classList.contains('hero-subject')){\nel.style.transform=`translate3d(${x+p*18}px,${y*.62}px,0) scale(${1+p*.018})`}"
new_subject = "else if(el.classList.contains('hero-subject')){\nif(desktop())el.style.transform=`translate3d(${x+p*18}px,${y*.62}px,0) scale(${1+p*.018})`;\nelse el.style.transform='translate3d(0,0,0)' }"
if old_subject in s:
    s = s.replace(old_subject, new_subject, 1)

if 'masck-hero-caucasian-mask-v1.webp' in s:
    raise RuntimeError('old portrait reference returned')
if 'updateHeaderVisibility();' in s:
    raise RuntimeError('stale navbar call returned')
if s.count('hero-mask-wrap hero-subject') != 1:
    raise RuntimeError('hero product wrapper count invalid')
if s.count(FALLBACK_URL) < 2:
    raise RuntimeError('stable product render not used for both hero and journey')
if new_mobile not in s:
    raise RuntimeError('mobile stability css missing')
if new_timing not in s:
    raise RuntimeError('mobile handoff timing missing')

INDEX.write_text(s)
print('mobile mask repair v2 complete')
