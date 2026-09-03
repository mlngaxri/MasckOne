from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'website/index.html'
s = INDEX.read_text()

css = r'''
/* Editorial finish polish v4 */
.header{
  background:rgba(248,250,248,.82);
  box-shadow:0 12px 34px rgba(24,33,28,.065),inset 0 1px 0 rgba(255,255,255,.46);
}
.nav{background:rgba(24,33,28,.04)}
.nav button{font-weight:500;transition:background .28s var(--ease),color .28s var(--ease),transform .28s var(--ease),box-shadow .28s var(--ease)}
.nav button.active{box-shadow:0 5px 16px rgba(24,33,28,.11)}
.nav-progress{background:rgba(24,33,28,.055)}
.nav-progress-fill{background:#75866c}

.hero-copy{top:15.4vh;width:min(455px,34vw)}
.hero h1{font-size:clamp(58px,6.15vw,94px);line-height:.825;letter-spacing:-.059em}
.hero-copy p{max-width:350px;margin-top:24px;padding-top:15px;color:rgba(24,33,28,.76);opacity:1}
.hero-clouds.hero-sky-orb{right:9.5vw;top:15vh;width:clamp(330px,36vw,520px);opacity:.82;filter:saturate(.78) brightness(1.015)}
.hero-mask-wrap.hero-subject{right:8vw;top:13.5vh;width:clamp(400px,40vw,590px)}
.hero-mask-product{filter:drop-shadow(0 18px 26px rgba(24,33,28,.115)) drop-shadow(0 42px 58px rgba(24,33,28,.09))}
.hero-bottom{bottom:23px;opacity:.46}

.band{box-shadow:0 15px 36px rgba(24,33,28,.045)}
.band.masck{background:rgba(250,248,241,.975)}
.band.one{background:rgba(24,33,28,.975)}

.handoff-page{background:linear-gradient(148deg,#f7f2e9 0%,#ebefea 47%,#dde8e9 100%)}
.handoff-stage:before{background:radial-gradient(circle at 50% 51%,rgba(255,255,255,.68),transparent 34%),linear-gradient(90deg,transparent 49.94%,rgba(24,33,28,.065) 50%,transparent 50.06%)}
.mask-orbit-overlay{width:clamp(620px,58vw,900px);scale:none}
.mask-orbit-node span{font-size:clamp(46px,4.85vw,80px);text-shadow:0 7px 24px rgba(246,241,232,.6)}
.handoff-halo{width:clamp(420px,46vw,700px);height:clamp(220px,20vw,315px);border-color:rgba(24,33,28,.15)}
.handoff-halo:before,.handoff-halo:after{border-color:rgba(24,33,28,.10)}
.handoff-halo .orbit{border-color:rgba(185,126,101,.2)}
.handoff-caption{bottom:46px;width:min(500px,39vw);font-size:13px;line-height:1.68}
.handoff-caption:before{width:68px;margin-bottom:16px;background:linear-gradient(90deg,var(--clay),#75866c 68%,rgba(24,33,28,.12))}
.handoff-caption b{margin-bottom:11px;font-size:clamp(27px,2.15vw,34px);letter-spacing:-.042em}
.handoff-caption span{max-width:390px;color:rgba(24,33,28,.69);opacity:1}

.page{padding-top:118px;gap:6vw}
.page h2{line-height:.875;letter-spacing:-.058em}
.page-copy>p{max-width:430px;color:currentColor;opacity:.69}
.page-label{margin-bottom:20px;opacity:.56}
.detail-grid{margin-top:40px;border-top-color:color-mix(in srgb,currentColor 30%,transparent)}
.detail-card{opacity:.72;line-height:1.62}
.section-tag{opacity:.48}
.visual img{filter:drop-shadow(0 16px 22px rgba(24,33,28,.075)) drop-shadow(0 36px 48px rgba(24,33,28,.08))}

.motion-paused .mask-orbit-node,.motion-paused .mask-orbit-node span{animation-play-state:paused!important}
.handoff-halo.motion-paused:after{animation-play-state:paused!important}

@media(min-width:901px) and (max-width:1180px){
  .hero-copy{top:15vh;width:min(390px,37vw)}
  .hero-mask-wrap.hero-subject{right:1vw;top:16vh;width:clamp(420px,47vw,550px)}
  .hero-clouds.hero-sky-orb{right:3vw;top:18vh;width:clamp(340px,41vw,480px)}
  .handoff-caption{width:min(440px,42vw)}
}

@media(max-width:900px){
  .header{top:max(10px,env(safe-area-inset-top));width:calc(100vw - 18px);background:rgba(248,250,248,.88);box-shadow:0 8px 24px rgba(24,33,28,.06),inset 0 1px 0 rgba(255,255,255,.46)}
  .nav button{font-size:9.25px}
  .hero-copy{top:11.8svh}
  .hero h1{max-width:80%;font-size:clamp(44px,12.4vw,61px);line-height:.87}
  .hero-copy p{max-width:74%;margin-top:16px;padding-top:10px;font-size:clamp(12px,3.05vw,12.5px);line-height:1.6}
  .hero-clouds.hero-sky-orb{right:1vw;top:28.5svh;width:64vw;opacity:.68;filter:saturate(.74)}
  .hero-mask-wrap.hero-subject{right:0;top:35svh;width:68vw}
  .hero-mask-product{filter:drop-shadow(0 15px 22px rgba(24,33,28,.11))}
  .band{left:-22vw;width:144vw;height:clamp(56px,15vw,64px)}
  .band span{font-size:clamp(37px,10.8vw,44px)}
  .band.masck{top:51%}.band.one{top:66.5%}
  .mask-journey{width:68vw;max-width:370px}
  .mask-orbit-overlay{width:min(91vw,455px)}
  .mask-orbit-node span{font-size:clamp(25px,7vw,35px);text-shadow:0 4px 14px rgba(246,241,232,.5)}
  .handoff-halo{width:min(81vw,390px);height:min(41vw,210px)}
  .handoff-caption{left:22px;right:22px;bottom:max(24px,env(safe-area-inset-bottom));max-width:390px;font-size:12px}
  .handoff-caption b{font-size:clamp(24px,6.6vw,29px)}
  .page{padding:84px 22px max(62px,calc(46px + env(safe-area-inset-bottom)));gap:22px}
  .visual{height:42svh;min-height:290px}
  .page h2{font-size:clamp(42px,11.5vw,60px);line-height:.9}
  .page-copy>p{font-size:12.5px;line-height:1.66}
  .detail-grid{margin-top:30px}
}

@media(max-width:390px){
  .nav button{font-size:9px;padding-inline:7px}
  .hero h1{max-width:90%;font-size:clamp(41px,13vw,53px)}
  .hero-copy p{max-width:82%}
  .hero-clouds.hero-sky-orb{right:-2vw;top:31svh;width:67vw}
  .hero-mask-wrap.hero-subject{right:-2vw;top:38svh;width:71vw}
  .band{left:-28vw;width:156vw}
}

@media(max-width:900px) and (max-height:620px) and (orientation:landscape){
  .header{top:max(7px,env(safe-area-inset-top))}
  .hero-copy{top:15svh}
  .hero-clouds.hero-sky-orb{right:5vw;top:15svh;width:41vw}
  .hero-mask-wrap.hero-subject{right:7vw;top:19svh;width:43vw}
  .band.masck{top:57%}.band.one{top:75%}
}
'''

if '/* Editorial finish polish v4 */' not in s:
    s = s.replace('\n</style>\n</head>', css + '\n</style>\n</head>', 1)

# Pause hero marquee animation once the hero is completely off-screen.
anchor = "const haloStream=document.querySelector('.handoff-halo-stream');\n"
insert = """const haloStream=document.querySelector('.handoff-halo-stream');
const bandTracks=[...document.querySelectorAll('.hero .band-track')];
let orbitMotionOn=true,haloMotionOn=true;
function setOrbitMotion(on){if(on===orbitMotionOn)return;orbitMotionOn=on;orbitCopies.forEach(el=>el.classList.toggle('motion-paused',!on))}
function setHaloMotion(on){if(on===haloMotionOn)return;haloMotionOn=on;if(haloStream)haloStream.classList.toggle('motion-paused',!on)}
if(hero&&'IntersectionObserver' in window){new IntersectionObserver(([entry])=>{bandTracks.forEach(track=>track.style.animationPlayState=entry.isIntersecting?'running':'paused')},{threshold:.01}).observe(hero)}
"""
if 'const bandTracks=[' not in s:
    s = s.replace(anchor, insert, 1)

old_orbit = "orbitCopies.forEach(el=>{el.style.opacity=String(textOpacity);el.style.setProperty('--stream-y',`${textY}px`)});"
new_orbit = "orbitCopies.forEach(el=>{el.style.opacity=String(textOpacity);el.style.setProperty('--stream-y',`${textY}px`)});setOrbitMotion(textOpacity>.012);"
s = s.replace(old_orbit, new_orbit, 1)

old_halo = "if(haloStream){haloStream.style.opacity=String(haloOpacity);haloStream.style.setProperty('--halo-y',`${haloY}px`)}"
new_halo = "if(haloStream){haloStream.style.opacity=String(haloOpacity);haloStream.style.setProperty('--halo-y',`${haloY}px`)}setHaloMotion(haloOpacity>.012);"
s = s.replace(old_halo, new_halo, 1)

old_else = "}else if(journey){journey.style.opacity='0';orbitCopies.forEach(el=>el.style.opacity='0');if(haloStream)haloStream.style.opacity='0'}"
new_else = "}else if(journey){journey.style.opacity='0';orbitCopies.forEach(el=>el.style.opacity='0');if(haloStream)haloStream.style.opacity='0';setOrbitMotion(false);setHaloMotion(false)}"
s = s.replace(old_else, new_else, 1)

if '/* Editorial finish polish v4 */' not in s:
    raise RuntimeError('v4 polish css missing')
if 'const bandTracks=[' not in s:
    raise RuntimeError('offscreen marquee pausing missing')
if 'setOrbitMotion(textOpacity>.012)' not in s:
    raise RuntimeError('orbit pausing missing')
if 'setHaloMotion(haloOpacity>.012)' not in s:
    raise RuntimeError('halo pausing missing')

INDEX.write_text(s)
print('editorial finish polish v4 complete')
