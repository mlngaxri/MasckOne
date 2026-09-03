from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'website/index.html'
s = INDEX.read_text()

PRODUCT = 'https://masck-one.vercel.app/images/masck-one-product-angle.webp'

# One physical DOM mask from the first viewport through the Architecture handoff.
# The old implementation cross-faded two copies of the same image, which could
# never be pixel-identical once each copy had its own sizing/transform state.
static = f'<div class="hero-mask-wrap hero-subject" data-depth=".52"><img class="hero-mask-product" src="{PRODUCT}" alt="MASCK ONE product render" fetchpriority="high" /></div>\n'
s = s.replace(static, '', 1)

old_journey = f'<div class="mask-journey" aria-hidden="true"><img src="{PRODUCT}" alt="" /></div>'
new_journey = f'<div class="mask-journey hero-mask-single" role="img" aria-label="MASCK ONE product render"><img src="{PRODUCT}" alt="" fetchpriority="high" decoding="async" /></div>'
if old_journey in s:
    s = s.replace(old_journey, new_journey, 1)
elif new_journey not in s:
    raise RuntimeError('single mask handoff markup not found')

# Remove the old second-mask reference/crossfade code.
s = s.replace("const heroSubject=document.querySelector('.hero-subject');\n", '', 1)
s = s.replace("else if(el.classList.contains('hero-subject')){\nif(desktop())el.style.transform=`translate3d(${x+p*18}px,${y*.62}px,0) scale(${1+p*.018})`;\nelse el.style.transform='translate3d(0,0,0)' }\n", '', 1)

old_motion = '''const isDesktop=desktop();
const detach=isDesktop?smooth(clamp((sy-heroH*.20)/(heroH*.66),0,1)):smooth(clamp((sy-heroH*.62)/(heroH*.30),0,1));
const show=isDesktop?smooth(clamp((sy-heroH*.06)/(heroH*.16),0,1)):smooth(clamp((sy-heroH*.61)/(heroH*.11),0,1));
const textEnter=smooth(clamp((sy-heroH*.72)/(innerHeight*.72),0,1));'''
new_motion = '''const isDesktop=desktop();
const detach=isDesktop?smooth(clamp((sy-heroH*.20)/(heroH*.66),0,1)):smooth(clamp((sy-heroH*.62)/(heroH*.30),0,1));
const textEnter=smooth(clamp((sy-heroH*.72)/(innerHeight*.72),0,1));'''
if old_motion in s:
    s = s.replace(old_motion, new_motion, 1)

old_geom = '''const sx=innerWidth*(isDesktop?.72:.67),sy0=innerHeight*(isDesktop?.55:.54),cx=innerWidth*.5,cy=innerHeight*.52;
const x=mix(sx,cx,detach),y=mix(sy0,cy,detach),scale=mix(1,isDesktop?.72:.82,detach);
journey.style.opacity=String(show);journey.style.transform=`translate3d(${x}px,${y}px,0) translate(-50%,-50%) scale(${scale}) rotate(${mix(-4,0,detach)}deg)`;
if(heroSubject)heroSubject.style.opacity=String(1-show);'''
new_geom = '''const w=journey.offsetWidth,h=journey.offsetHeight;
const small=innerWidth<=390;
let rightPx,topPx;
if(isDesktop&&innerWidth<=1180){rightPx=innerWidth*.01;topPx=innerHeight*.16}
else if(isDesktop){rightPx=innerWidth*.08;topPx=innerHeight*.135}
else if(small){rightPx=-innerWidth*.02;topPx=innerHeight*.385}
else{rightPx=0;topPx=innerHeight*.355}
const heroPX=isDesktop?(mx*.52*24+p*18)*(1-detach):0;
const heroPY=isDesktop?(my*.52*15+p*.52*92)*.62*(1-detach):0;
const sx=innerWidth-rightPx-w*.5+heroPX,sy0=topPx+h*.5+heroPY,cx=innerWidth*.5,cy=innerHeight*.52;
const x=mix(sx,cx,detach),y=mix(sy0,cy,detach),scale=mix(1,isDesktop?.72:.82,detach);
journey.style.opacity='1';
journey.style.zIndex=sy>heroH*.74?'1120':'5';
journey.style.transform=`translate3d(${x}px,${y}px,0) translate(-50%,-50%) scale(${scale}) rotate(${mix(-4,0,detach)}deg)`;'''
if old_geom in s:
    s = s.replace(old_geom, new_geom, 1)
elif new_geom not in s:
    raise RuntimeError('old two-mask geometry not found')

# The single mask must not inherit the old circular glow. Anything behind the
# transparent eye/nose apertures should be the actual page beneath the product.
css = r'''
/* Single physical mask continuity v6 */
.hero-mask-wrap.hero-subject{display:none!important}
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
  filter:none;
  transform:translate3d(-50%,-50%,0);
  transform-origin:50% 50%;
  will-change:transform;
}
.mask-journey.hero-mask-single img{
  width:100%;
  height:100%;
  object-fit:contain;
  background:transparent!important;
  filter:drop-shadow(0 18px 26px rgba(24,33,28,.115)) drop-shadow(0 42px 58px rgba(24,33,28,.09));
  backface-visibility:hidden;
  -webkit-backface-visibility:hidden;
}
.mask-journey.hero-mask-single:after{content:none!important;display:none!important}
@media(min-width:901px) and (max-width:1180px){
  .mask-journey.hero-mask-single{width:clamp(420px,47vw,550px)}
}
@media(max-width:900px){
  .mask-journey.hero-mask-single{width:67vw;max-width:none;will-change:transform}
  .mask-journey.hero-mask-single img{filter:drop-shadow(0 15px 22px rgba(24,33,28,.11))}
}
@media(max-width:390px){
  .mask-journey.hero-mask-single{width:69vw}
}
'''
if '/* Single physical mask continuity v6 */' not in s:
    s = s.replace('\n</style>\n</head>', css + '\n</style>\n</head>', 1)

# Hard failures for any accidental reintroduction of the two-mask system.
if 'hero-mask-wrap hero-subject' in s:
    raise RuntimeError('static hero mask copy still present')
if 'const heroSubject=' in s or 'heroSubject.style.opacity' in s:
    raise RuntimeError('old hero/journey crossfade still present')
if s.count('mask-journey hero-mask-single') != 1:
    raise RuntimeError('expected exactly one physical mask element')
if s.count(PRODUCT) < 1:
    raise RuntimeError('mask source missing')
if 'journey.style.opacity=String(show)' in s:
    raise RuntimeError('old journey fade still present')
if '.mask-journey.hero-mask-single:after{content:none!important;display:none!important}' not in s:
    raise RuntimeError('transparent-aperture protection missing')

INDEX.write_text(s)
print('single physical mask continuity v6 complete')
