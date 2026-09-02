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

old_subject = "else if(el.classList.contains('hero-subject')){\nel.style.transform=`translate3d(${x+p*18}px,${y*.62}px,0) scale(${1+p*.018})`}"
new_subject = "else if(el.classList.contains('hero-subject')){\nif(desktop())el.style.transform=`translate3d(${x+p*18}px,${y*.62}px,0) scale(${1+p*.018})`;\nelse el.style.transform='translate3d(0,0,0)' }"
if old_subject in s:
    s = s.replace(old_subject, new_subject, 1)

# Phones use native touch scrolling. This avoids a second always-running RAF loop
# while desktop keeps the intended smooth wheel treatment.
s = s.replace(
    "const lenis=window.Lenis?new Lenis({autoRaf:true,lerp:.085,smoothWheel:true,syncTouch:false,wheelMultiplier:.92,touchMultiplier:1,overscroll:false}):null;",
    "const lenis=window.Lenis&&desktop()?new Lenis({autoRaf:true,lerp:.085,smoothWheel:true,syncTouch:false,wheelMultiplier:.92,touchMultiplier:1,overscroll:false}):null;",
    1,
)

# Mobile scroll choreography follows native scroll exactly instead of trailing.
s = s.replace(
    "sy+=(scrollY-sy)*(desktop()?.13:.28);",
    "sy=desktop()?sy+(scrollY-sy)*.13:scrollY;",
    1,
)

# Glimmers are retained on desktop but disabled on touch/mobile to preserve frame rate.
s = s.replace(
    "if(lowMotion()||document.hidden)return;",
    "if(!desktop()||lowMotion()||document.hidden)return;",
    1,
)

# Later mobile crossfade keeps one visible mask at a time.
s = s.replace(
    "const detach=isDesktop?smooth(clamp((sy-heroH*.20)/(heroH*.66),0,1)):smooth(clamp((sy-heroH*.60)/(heroH*.32),0,1));\nconst show=isDesktop?smooth(clamp((sy-heroH*.06)/(heroH*.16),0,1)):smooth(clamp((sy-heroH*.58)/(heroH*.12),0,1));",
    "const detach=isDesktop?smooth(clamp((sy-heroH*.20)/(heroH*.66),0,1)):smooth(clamp((sy-heroH*.62)/(heroH*.30),0,1));\nconst show=isDesktop?smooth(clamp((sy-heroH*.06)/(heroH*.16),0,1)):smooth(clamp((sy-heroH*.61)/(heroH*.11),0,1));",
    1,
)

polish_css = r'''
/* Responsive performance polish v3 */
.header{-webkit-backdrop-filter:blur(18px) saturate(1.08)}
.hero h1,.page h2,.handoff-caption b{font-kerning:normal}
.hero-copy p,.page-copy>p,.handoff-caption span{text-wrap:pretty}

@media(min-width:901px) and (max-width:1180px){
  .header{width:min(94vw,1080px)}
  .hero-copy{left:clamp(34px,4.2vw,54px);width:min(390px,36vw)}
  .hero h1{font-size:clamp(56px,6.1vw,78px)}
  .hero-mask-wrap.hero-subject{right:-1vw;width:clamp(430px,49vw,570px)}
  .hero-clouds.hero-sky-orb{right:1vw;width:clamp(360px,44vw,510px)}
}

@media(max-width:900px){
  body:after{display:none}
  .header{top:12px;width:calc(100vw - 20px);height:50px;padding:0 7px 0 14px;backdrop-filter:blur(9px) saturate(1.04);-webkit-backdrop-filter:blur(9px) saturate(1.04);box-shadow:0 9px 28px rgba(24,33,28,.065),inset 0 1px 0 rgba(255,255,255,.32)}
  .brand{font-size:8.5px;letter-spacing:.18em}
  .nav{gap:1px;padding:2px}
  .nav button{min-height:38px;padding:8px 9px;font-size:8.5px;letter-spacing:.015em}
  .nav-progress-fill{box-shadow:none}

  .hero{height:100svh;min-height:680px}
  .hero-copy{top:11.5svh;left:22px;right:22px}
  .hero h1{max-width:76%;font-size:clamp(44px,12.6vw,62px);line-height:.86;letter-spacing:-.056em}
  .hero-copy p{max-width:72%;margin-top:17px;padding-top:10px;font-size:clamp(11.25px,3vw,12px);line-height:1.62}
  .hero-clouds.hero-sky-orb{right:-1vw;top:27svh;width:68vw;opacity:.70;filter:saturate(.78)}
  .hero-mask-wrap.hero-subject{right:-2vw;top:34svh;width:72vw;max-width:none;will-change:opacity}
  .hero-mask-product{filter:drop-shadow(0 18px 28px rgba(24,33,28,.12))}

  .band{left:-24vw;width:148vw;height:clamp(58px,16vw,68px);contain:paint}
  .band span{font-size:clamp(38px,11.6vw,46px)}
  .band.masck{top:50%}
  .band.one{top:66%}
  .band-track{animation-duration:42s}
  .band.one .band-track{animation-duration:48s}

  .mask-journey{width:72vw;max-width:390px;filter:none;will-change:transform,opacity}
  .mask-journey img{filter:drop-shadow(0 16px 25px rgba(24,33,28,.12))}
  .mask-journey:after{inset:18%;filter:blur(7px);opacity:.7}
  .mask-orbit-overlay{width:min(94vw,480px);will-change:transform,opacity}
  .mask-orbit-node{animation-duration:22s}
  .mask-orbit-node span{font-size:clamp(25px,7vw,36px);text-shadow:0 5px 18px rgba(246,241,232,.54);animation-duration:22s}
  .handoff-halo{width:min(84vw,410px);height:min(43vw,225px);will-change:transform,opacity}
  .handoff-halo:after{animation-duration:30s}
  .handoff-stage:before{background:radial-gradient(circle at 50% 52%,rgba(255,255,255,.48),transparent 34%),linear-gradient(90deg,transparent 49.92%,rgba(24,33,28,.065) 50%,transparent 50.08%)}
  .handoff-caption{left:22px;right:22px;bottom:26px;width:auto;max-width:410px;font-size:11.5px;line-height:1.64}
  .handoff-caption b{font-size:clamp(23px,6.4vw,28px);line-height:1.02}

  .page{padding:82px 22px 60px;gap:20px}
  .visual{height:43svh;min-height:300px}
  .visual:before{filter:blur(6px)}
  .visual:after{filter:blur(8px)}
  .page h2{font-size:clamp(42px,11.8vw,62px);line-height:.88;letter-spacing:-.055em}
  .page-copy>p{font-size:12.25px;line-height:1.68}
  .page-label,.section-tag,.page-index{letter-spacing:.11em}
  .detail-card{font-size:10.5px;line-height:1.55}
  .glimmer-pass{display:none!important}
}

@media(max-width:390px){
  .header{top:9px;width:calc(100vw - 14px);padding:0 6px;grid-template-columns:1fr}
  .brand{display:none}
  .nav{justify-self:center}
  .nav button{padding-inline:8px;font-size:8.25px}
  .hero-copy{left:18px;right:18px;top:11svh}
  .hero h1{max-width:88%;font-size:clamp(42px,13.4vw,54px)}
  .hero-copy p{max-width:78%;font-size:11.25px}
  .hero-clouds.hero-sky-orb{right:-5vw;top:30svh;width:72vw}
  .hero-mask-wrap.hero-subject{right:-5vw;top:37svh;width:76vw}
  .hero-bottom{left:18px;right:18px}
  .handoff-caption{left:18px;right:18px}
  .page{padding-left:18px;padding-right:18px}
}

@media(max-width:900px) and (max-height:620px) and (orientation:landscape){
  .hero{min-height:100svh}
  .header{top:8px;height:44px}
  .hero-copy{top:15svh;left:24px}
  .hero h1{max-width:50%;font-size:clamp(38px,7.2vw,54px)}
  .hero-copy p{max-width:45%;margin-top:12px;font-size:10.5px;line-height:1.5}
  .hero-clouds.hero-sky-orb{right:4vw;top:13svh;width:44vw}
  .hero-mask-wrap.hero-subject{right:5vw;top:18svh;width:46vw}
  .band{height:48px}
  .band span{font-size:34px}
  .band.masck{top:56%}
  .band.one{top:74%}
  .hero-bottom{display:none}
  .handoff-caption{bottom:16px;max-width:48vw}
  .visual{height:62svh;min-height:250px}
}

@media(max-width:900px) and (prefers-reduced-motion:reduce){
  .hero-clouds.hero-sky-orb,.hero-mask-wrap.hero-subject{will-change:auto}
  .mask-orbit-overlay,.handoff-halo,.mask-journey{will-change:auto}
}
'''
if '/* Responsive performance polish v3 */' not in s:
    s = s.replace('\n</style>\n</head>', polish_css + '\n</style>\n</head>', 1)

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
if '/* Responsive performance polish v3 */' not in s:
    raise RuntimeError('responsive polish missing')
if 'sy=desktop()?sy+(scrollY-sy)*.13:scrollY;' not in s:
    raise RuntimeError('native mobile scroll tracking missing')
if 'window.Lenis&&desktop()?' not in s:
    raise RuntimeError('mobile Lenis disable missing')

INDEX.write_text(s)
print('responsive motion and typography polish complete')
