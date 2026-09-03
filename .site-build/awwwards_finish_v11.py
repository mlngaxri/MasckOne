from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'website/index.html'

s = INDEX.read_text()

# Editorial display face. Keep Manrope for copy and DM Mono for engineering metadata.
font_link = '<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400&family=Instrument+Serif:ital@0;1&family=Manrope:wght@400;500;600&display=swap" rel="stylesheet" />'
s = re.sub(r'<link href="https://fonts\.googleapis\.com/css2\?family=DM\+Mono[^>]+>', font_link, s, count=1)

START = '/* Awwwards editorial finish v11 */'
END = '/* End Awwwards editorial finish v11 */'
s = re.sub(re.escape(START) + r'.*?' + re.escape(END) + r'\n?', '', s, flags=re.S)

css = r'''
/* Awwwards editorial finish v11 */
:root{
  --display:"Instrument Serif",Georgia,serif;
  --sans:Manrope,system-ui,sans-serif;
  --mono:"DM Mono",monospace;
  --hairline:rgba(24,33,28,.12);
  --muted-ink:rgba(24,33,28,.62);
  --surface-glass:rgba(249,250,247,.82);
}
html{font-size:16px}
body{
  font-family:var(--sans);
  font-feature-settings:"kern" 1,"liga" 1;
  letter-spacing:-.006em;
}
body:before{inset:7px;border-color:rgba(24,33,28,.085);border-radius:18px}
body:after{opacity:.022}

/* Navigation: quieter, more architectural, less decorative. */
.header{
  top:18px;
  width:min(94vw,1040px);
  height:50px;
  padding:0 7px 0 18px;
  border:1px solid rgba(24,33,28,.105);
  background:var(--surface-glass);
  background-image:none;
  backdrop-filter:blur(22px) saturate(1.08);
  box-shadow:0 8px 30px rgba(24,33,28,.055),inset 0 1px 0 rgba(255,255,255,.55);
  animation:none;
}
.brand{
  font-family:var(--mono);
  font-size:9px;
  font-weight:400;
  letter-spacing:.19em;
}
.nav{gap:0;padding:2px;background:rgba(24,33,28,.038)}
.nav button{
  min-height:32px;
  padding:7px 13px;
  font-family:var(--mono);
  font-size:8px;
  font-weight:400;
  letter-spacing:.075em;
  text-transform:uppercase;
  color:rgba(24,33,28,.58);
  transition:color .28s var(--ease),background .28s var(--ease),transform .28s var(--ease),box-shadow .28s var(--ease);
}
.nav button.active{
  color:#f8f9f4;
  background:#1a211d;
  box-shadow:inset 0 0 0 1px rgba(255,255,255,.045),0 3px 12px rgba(24,33,28,.10);
}
.nav-progress{height:1px;background:rgba(24,33,28,.07)}
.nav-progress-fill{background:#77866f;box-shadow:none}
@media(hover:hover) and (pointer:fine){
  .nav button:not(.active):hover{background:rgba(24,33,28,.055);color:rgba(24,33,28,.88);transform:none}
}

/* Display typography: one editorial voice across every chamber. */
.hero h1,.page h2,.handoff-caption b,.mask-orbit-node span,
.systems-copy h2,.systems-word,.systems-step b,.section-tag b{
  font-family:var(--display);
  font-weight:400;
  font-style:normal;
  font-variation-settings:normal;
  font-feature-settings:"kern" 1,"liga" 1;
}
.hero h1{
  max-width:560px;
  font-size:clamp(66px,6.8vw,108px);
  line-height:.79;
  letter-spacing:-.052em;
}
.hero h1 span+span{margin-left:.13em}
.hero-copy{top:14.4svh;width:min(500px,38vw)}
.hero-copy p{
  max-width:370px;
  margin-top:27px;
  padding-top:13px;
  border-top-color:rgba(24,33,28,.16);
  font-size:12px;
  line-height:1.68;
  letter-spacing:-.006em;
  color:rgba(24,33,28,.66);
  opacity:1;
  text-wrap:pretty;
}
.hero-bottom{bottom:24px;font-size:7px;letter-spacing:.13em;opacity:.44}
.hero-bottom .line{height:1px;opacity:.65}
.hero-clouds.hero-sky-orb{opacity:.62;filter:saturate(.70) contrast(.98)}

/* Campaign ribbons become supporting art direction, not the loudest typography. */
.band{border-block-color:rgba(24,33,28,.075);box-shadow:none}
.band span{
  font-family:var(--display);
  font-weight:400;
  font-size:clamp(30px,3.15vw,47px);
  letter-spacing:-.032em;
}
.band.masck{background:rgba(249,249,244,.93)}
.band.one{background:rgba(25,32,28,.955)}
.band-track{animation-duration:38s}
.band.one .band-track{animation-duration:44s}
.band i{font-family:var(--mono);font-size:.27em;margin:0 1.05em;color:#a96f58}

/* Architecture handoff. */
.handoff-stage:before{opacity:.62}
.handoff-caption{width:min(520px,44vw);font-size:12px}
.handoff-caption b{
  margin-bottom:9px;
  max-width:500px;
  font-size:clamp(34px,2.9vw,48px);
  line-height:.96;
  letter-spacing:-.045em;
}
.handoff-caption span{max-width:410px;line-height:1.65;color:rgba(24,33,28,.58)}
.mask-orbit-node span{
  font-size:clamp(39px,5.25vw,76px);
  letter-spacing:-.045em;
  text-shadow:none;
}
.handoff-halo{opacity:.76}

/* Proof pages: larger editorial type, quieter technical UI. */
.page{
  padding-top:110px;
  grid-template-columns:minmax(310px,.76fr) 1.24fr;
  gap:6.8vw;
}
.page-copy{max-width:560px}
.page-label,.section-tag,.page-index,.evidence-line{
  font-family:var(--mono);
}
.page-label{
  margin-bottom:20px;
  font-size:7.5px;
  letter-spacing:.14em;
  opacity:.46;
}
.page h2{
  max-width:590px;
  font-size:clamp(62px,6.7vw,102px);
  line-height:.82;
  letter-spacing:-.052em;
}
.page-copy>p{
  max-width:430px;
  margin-top:27px;
  font-size:12.25px;
  line-height:1.7;
  color:color-mix(in srgb,currentColor 67%,transparent);
  opacity:1;
  text-wrap:pretty;
}
.section-tag{
  top:91px;
  min-width:148px;
  padding-top:7px;
  border-top-color:color-mix(in srgb,currentColor 22%,transparent);
  font-size:7px;
  letter-spacing:.14em;
  opacity:.55;
}
.section-tag b{font-size:23px;letter-spacing:-.03em}
.detail-grid{margin-top:42px;border-top-color:color-mix(in srgb,currentColor 20%,transparent)}
.detail-card{
  min-height:104px;
  padding-top:17px;
  font-size:10.5px;
  line-height:1.62;
  color:color-mix(in srgb,currentColor 68%,transparent);
  opacity:1;
}
.detail-card b{
  margin-bottom:15px;
  font-family:var(--mono);
  font-size:7px;
  font-weight:400;
  letter-spacing:.14em;
}
.detail-card:before{font-size:6.5px;opacity:.34}
.visual:before{opacity:.46;filter:blur(15px)}
.visual:after{opacity:.24}
.visual img{filter:drop-shadow(0 18px 24px rgba(24,33,28,.07)) drop-shadow(0 42px 54px rgba(24,33,28,.07))}
.page.dark{background:#171e1a}
.page.clay{background:#b77c63}
.page-index,.evidence-line{font-size:7px;letter-spacing:.085em;opacity:.34}

/* Systems: bring the experimental chamber into the same editorial language. */
.systems-experience{background:#161d19}
.systems-sticky{background:#161d19}
.systems-copy{width:min(520px,38vw)}
.systems-copy-motion{width:min(500px,36vw)}
.systems-copy h2{
  font-size:clamp(60px,6.35vw,100px);
  line-height:.82;
  letter-spacing:-.052em;
}
.systems-copy p{
  max-width:400px;
  margin-top:25px;
  padding-top:13px;
  font-size:12px;
  line-height:1.7;
  color:rgba(245,246,239,.63);
  text-wrap:pretty;
}
.systems-kicker{
  margin-bottom:21px;
  font-size:7px;
  letter-spacing:.15em;
  color:rgba(245,246,239,.48);
}
.systems-word{
  font-size:clamp(170px,23vw,370px);
  line-height:.68;
  letter-spacing:-.06em;
  opacity:.045;
}
.systems-step{
  top:90px;
  border-top-color:rgba(255,255,255,.16);
  font-size:7px;
  color:rgba(255,255,255,.46);
}
.systems-step b{font-size:38px;letter-spacing:-.03em}
.systems-facts{margin-top:35px;border-top-color:rgba(255,255,255,.14);font-size:9.5px;color:rgba(245,246,239,.50)}
.systems-facts b{font-size:7px;font-weight:400}
.systems-grid{opacity:.055}
.systems-readout{font-size:7px;color:rgba(245,246,239,.37)}
.systems-timeline{font-size:6.5px;letter-spacing:.15em;color:rgba(245,246,239,.37)}
.systems-timeline-track{width:138px;background:rgba(245,246,239,.12)}
.systems-timeline-fill{background:#b8c8ae}
.systems-timeline-dot{border-color:#b8c8ae;background:#161d19}
.systems-evidence{font-size:7px;color:rgba(245,246,239,.28)}

/* Motion remains expressive, but the UI responds with restraint. */
.reveal{transition-timing-function:var(--ease)}
@media(hover:hover) and (pointer:fine){
  .header:hover{box-shadow:0 10px 34px rgba(24,33,28,.07),inset 0 1px 0 rgba(255,255,255,.62)}
}

@media(max-width:900px){
  body:before{inset:5px;border-radius:14px;border-color:rgba(24,33,28,.065)}
  body:after{display:none}
  .header{
    top:max(9px,env(safe-area-inset-top));
    width:calc(100vw - 16px);
    height:47px;
    padding-left:12px;
    padding-right:5px;
    backdrop-filter:blur(16px) saturate(1.04);
  }
  .brand{font-size:8px;letter-spacing:.15em}
  .nav button{min-height:31px;padding:7px 8px;font-size:7.25px;letter-spacing:.055em}

  .hero-copy{top:12.5svh;left:22px;width:calc(100vw - 44px)}
  .hero h1{
    max-width:88vw;
    font-size:clamp(52px,15.2vw,72px);
    line-height:.80;
    letter-spacing:-.048em;
  }
  .hero h1 span+span{margin-left:.085em}
  .hero-copy p{max-width:72vw;margin-top:20px;padding-top:10px;font-size:11.5px;line-height:1.62}
  .hero-clouds.hero-sky-orb{top:30svh;width:61vw;opacity:.57}
  .band{height:clamp(53px,14vw,61px)}
  .band span{font-size:clamp(37px,10.5vw,44px)}
  .band-track{animation-duration:34s}
  .band.one .band-track{animation-duration:40s}
  .hero-bottom{left:22px;right:22px;bottom:max(19px,env(safe-area-inset-bottom));font-size:6.5px}

  .mask-orbit-node span{font-size:clamp(29px,8.2vw,40px)}
  .handoff-caption{left:22px;right:22px;width:auto;bottom:max(23px,env(safe-area-inset-bottom))}
  .handoff-caption b{font-size:clamp(30px,8.7vw,38px)}
  .handoff-caption span{font-size:11.5px;line-height:1.58}

  .page{padding:82px 22px max(60px,calc(44px + env(safe-area-inset-bottom)));gap:20px}
  .page h2{font-size:clamp(49px,14.2vw,70px);line-height:.83}
  .page-copy>p{margin-top:20px;font-size:11.75px;line-height:1.64}
  .page-label{margin-bottom:16px}
  .detail-grid{margin-top:28px}
  .detail-card{min-height:90px;font-size:10px}
  .visual{height:43svh;min-height:285px}
  .section-tag{top:72px;font-size:6.5px}
  .section-tag b{font-size:20px}

  .systems-copy,.systems-copy-motion{left:22px;right:22px;top:13.5svh;width:auto}
  .systems-copy h2{max-width:82vw;font-size:clamp(49px,14vw,70px);line-height:.82}
  .systems-copy p{max-width:78vw;margin-top:18px;padding-top:10px;font-size:11.5px;line-height:1.62}
  .systems-kicker{margin-bottom:16px}
  .systems-word{font-size:clamp(120px,37vw,190px);opacity:.04}
  .systems-step{top:max(70px,calc(env(safe-area-inset-top) + 59px));right:20px}
  .systems-step b{font-size:28px}
  .systems-core{top:62%;width:min(88vw,420px)}
  .systems-evidence{font-size:6.5px}
}

@media(max-width:390px){
  .brand{display:none}
  .header{grid-template-columns:1fr;justify-items:center;padding-inline:5px}
  .nav button{padding-inline:9px}
  .hero-copy{left:18px;width:calc(100vw - 36px)}
  .hero h1{font-size:clamp(48px,15.7vw,62px)}
  .hero-copy p{max-width:80vw}
  .page{padding-left:18px;padding-right:18px}
  .systems-copy,.systems-copy-motion{left:18px;right:18px}
}

@media(max-width:900px) and (max-height:620px) and (orientation:landscape){
  .hero-copy{top:16svh;left:24px;width:46vw}
  .hero h1{font-size:clamp(40px,7vw,58px);max-width:45vw}
  .hero-copy p{max-width:42vw;margin-top:12px;font-size:10.5px}
  .hero-clouds.hero-sky-orb{right:6vw;top:14svh;width:39vw}
  .systems-copy,.systems-copy-motion{top:18svh;left:24px;right:auto;width:43vw}
  .systems-copy h2{font-size:clamp(40px,6.5vw,56px);max-width:42vw}
  .systems-copy p{max-width:42vw;font-size:10.5px}
  .systems-core{left:72%;top:55%;width:min(48vw,340px)}
}
/* End Awwwards editorial finish v11 */
'''

s = s.replace('\n</style>\n</head>', '\n' + css + '\n</style>\n</head>', 1)

# Guard against regressions that previously damaged the product artwork.
assert s.count('mask-journey hero-mask-single') == 1
assert 'masck-aperture-mask' not in s
assert s.count('class="hero-mask-art"') == 1
assert START in s and END in s
assert 'Instrument+Serif' in s
assert 'animation:none;' in s[s.find('.header{', s.find(START)):]

INDEX.write_text(s)
print('Awwwards editorial finish v11 applied')
