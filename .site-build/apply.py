from pathlib import Path
import base64, hashlib, re
ROOT=Path(__file__).resolve().parents[1] if '.site-build' in str(Path(__file__)) else Path('/mnt/data/sitebuild-test')
INDEX=ROOT/'website/index.html'
EXPECTED_BLOB='27417e2a97a2b858a0f3ad4b8d16b2d7cc0531a7'

def git_blob_sha(data: bytes)->str:
    h=hashlib.sha1(); h.update(f'blob {len(data)}\0'.encode()); h.update(data); return h.hexdigest()

def once(text, old, new, label):
    n=text.count(old)
    if n!=1: raise RuntimeError(f'{label}: expected 1 match, got {n}')
    return text.replace(old,new,1)

raw=INDEX.read_bytes()
if git_blob_sha(raw)!=EXPECTED_BLOB:
    raise RuntimeError(f'Unexpected website baseline: {git_blob_sha(raw)}')
s=raw.decode()

# Stable viewport + Lenis + nav progress.
s=once(s,'html{background:var(--cloud);scroll-behavior:auto}', 'html{background:var(--cloud);scroll-behavior:auto;scrollbar-width:none;-ms-overflow-style:none}', 'html scrollbar')
s=once(s,'body{margin:0;background:var(--cloud);color:var(--ink);font-family:Manrope,system-ui,sans-serif;overflow-x:hidden;font-optical-sizing:auto;-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}', 'body{margin:0;background:var(--cloud);color:var(--ink);font-family:Manrope,system-ui,sans-serif;overflow-x:hidden;scrollbar-width:none;-ms-overflow-style:none;font-optical-sizing:auto;-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}\nhtml::-webkit-scrollbar,body::-webkit-scrollbar{width:0;height:0;display:none}\nhtml.lenis,html.lenis body{height:auto}.lenis.lenis-smooth{scroll-behavior:auto!important}.lenis.lenis-stopped{overflow:clip}', 'body scrollbar')
s=once(s,'.status-chip:before{content:"";width:6px;height:6px;border-radius:50%;background:#738269;box-shadow:0 0 0 5px rgba(115,130,105,.1)}', '.status-chip:before{content:"";width:6px;height:6px;border-radius:50%;background:#738269;box-shadow:0 0 0 5px rgba(115,130,105,.1)}\n.nav-progress{position:absolute;left:22px;right:22px;bottom:4px;height:1px;overflow:hidden;border-radius:999px;background:rgba(24,33,28,.095);pointer-events:none}\n.nav-progress-fill{position:absolute;inset:0;background:rgba(185,126,101,.9);transform:scaleX(0);transform-origin:left center;will-change:transform;box-shadow:0 0 7px rgba(185,126,101,.22)}', 'nav progress css')
s=once(s,'.header{top:14px;width:calc(100vw - 26px);height:50px;grid-template-columns:1fr auto;padding:0 8px 0 14px}', '.header{top:14px;width:calc(100vw - 26px);height:50px;grid-template-columns:1fr auto;padding:0 8px 0 14px}\n.nav-progress{left:15px;right:15px;bottom:3px}', 'mobile progress')
s=once(s,'<div class="status-chip">Engineering development</div>\n</header>', '<div class="status-chip">Engineering development</div>\n<div class="nav-progress" aria-hidden="true"><span class="nav-progress-fill"></span></div>\n</header>', 'progress html')
s=once(s,'</main>\n<script>', '</main>\n<script src="https://unpkg.com/lenis@1.3.26/dist/lenis.min.js"></script>\n<script>', 'lenis script')
s=once(s,"const heroCopy=document.querySelector('[data-depth-copy]');", "const heroCopy=document.querySelector('[data-depth-copy]');\n\nconst navProgressFill=document.querySelector('.nav-progress-fill');\n\nconst lenis=window.Lenis?new Lenis({autoRaf:true,lerp:.085,smoothWheel:true,syncTouch:false,wheelMultiplier:.92,touchMultiplier:1,overscroll:false}):null;", 'lenis refs')
s=once(s,"document.addEventListener('visibilitychange',()=>{\nif(document.hidden)clearTimeout(glimmerTimer);\nelse queueGlimmer(true)}\n);", "document.addEventListener('visibilitychange',()=>{\nif(document.hidden)clearTimeout(glimmerTimer);\nelse queueGlimmer(true)}\n);\n\nfunction updateNavProgress(position=scrollY){\nconst current=document.querySelector('.view.active');\nif(!current||!navProgressFill)return;\nconst max=Math.max(0,current.scrollHeight-innerHeight);\nconst progress=max>0?clamp(position/max,0,1):0;\nnavProgressFill.style.transform=`scaleX(${progress})`;\n}\n\nfunction jumpToTop(){\nif(lenis)lenis.scrollTo(0,{immediate:true,force:true});\nelse window.scrollTo(0,0);\n}", 'progress funcs')
s=once(s,'window.scrollTo(0,0);\nsy=0;\nrequestFrame();', 'jumpToTop();\nsy=0;\nif(lenis)lenis.resize();\nupdateNavProgress(0);\nrequestFrame();', 'set active')
s=once(s,"window.scrollTo({\ntop:0,behavior:'smooth'}\n);", "if(lenis)lenis.scrollTo(0,{duration:1.05});\nelse window.scrollTo({top:0,behavior:'smooth'});", 'same nav smooth')
s=once(s,"document.documentElement.style.overflow='hidden';", 'if(lenis)lenis.stop();', 'stop lenis')
s=once(s,"document.documentElement.style.overflow='';", 'if(lenis)lenis.start();', 'start lenis')
s=once(s,"addEventListener('scroll',requestFrame,{\npassive:true}\n);", "addEventListener('scroll',()=>{\nupdateNavProgress();\nrequestFrame()}\n,{passive:true});", 'scroll progress')
s=once(s,"addEventListener('resize',()=>{\nsy=scrollY;\nclearDesktopResidue();\nrequestFrame()}", "addEventListener('resize',()=>{\nsy=scrollY;\nif(lenis)lenis.resize();\nclearDesktopResidue();\nupdateNavProgress();\nrequestFrame()}", 'resize lenis')
s=once(s,'clearDesktopResidue();\nrequestFrame();', 'clearDesktopResidue();\nupdateNavProgress();\nrequestFrame();', 'initial progress')

# Cinematic hero + handoff CSS.
marker='@media(min-width:901px){'
css='''
/* Cinematic hero + scroll handoff */
.hero{background:#dfe8ed}
.hero-clouds.hero-bg{inset:-6%;width:112%;height:112%;opacity:1;filter:saturate(.84) brightness(1.02) contrast(.98);object-position:center center}
.hero-subject{z-index:4;right:2.5vw;left:auto;bottom:-7vh;height:112vh;width:auto;max-width:none;filter:drop-shadow(0 25px 48px rgba(24,33,28,.11));-webkit-mask-image:linear-gradient(90deg,transparent 0,#000 12%,#000 100%);mask-image:linear-gradient(90deg,transparent 0,#000 12%,#000 100%);transform-origin:58% 52%}
.hero-vignette{z-index:2;background:linear-gradient(90deg,rgba(225,235,240,.94) 0%,rgba(225,235,240,.67) 26%,rgba(225,235,240,.05) 54%,rgba(225,235,240,.02) 76%,rgba(225,235,240,.18) 100%),radial-gradient(circle at 72% 44%,transparent 0 26%,rgba(226,236,241,.08) 52%,rgba(226,236,241,.48) 100%)}
.hero-copy{z-index:8;top:14.2vh;width:min(450px,34vw)}
.hero h1{font-size:clamp(58px,6.25vw,96px);line-height:.81;max-width:510px}
.hero-copy p{max-width:330px}
.hero-meta{z-index:9}
.band{height:clamp(98px,9vw,142px);border-block-color:rgba(24,33,28,.14);box-shadow:0 18px 44px rgba(24,33,28,.06)}
.band span{font-size:clamp(55px,6vw,94px);letter-spacing:-.052em}
.band i{font-size:.26em;margin:0 .62em}
.band.masck{z-index:3;top:49%;background:rgba(250,248,241,.965)}
.band.one{z-index:6;top:67%;background:rgba(24,33,28,.965)}
.hero-bottom{z-index:10}
.mask-journey{position:fixed;z-index:1120;left:0;top:0;width:clamp(230px,27vw,430px);aspect-ratio:1;display:grid;place-items:center;pointer-events:none;opacity:0;transform:translate3d(-50%,-50%,0);will-change:transform,opacity;filter:drop-shadow(0 24px 48px rgba(24,33,28,.15))}
.mask-journey img{width:100%;height:100%;object-fit:contain;filter:drop-shadow(0 18px 32px rgba(24,33,28,.12))}
.mask-journey:after{content:"";position:absolute;inset:13%;border-radius:50%;background:radial-gradient(circle,rgba(255,255,255,.25),rgba(255,255,255,0) 68%);filter:blur(14px);z-index:-1}
.handoff-page{position:relative;height:132svh;background:linear-gradient(145deg,#f6f1e8 0%,#e9eee8 44%,#dce8eb 100%);border-top:1px solid var(--line);isolation:isolate}
.handoff-stage{position:sticky;top:0;height:100svh;overflow:hidden;display:grid;place-items:center;padding:92px var(--pad) 52px}
.handoff-stage:before{content:"";position:absolute;inset:0;background:radial-gradient(circle at 50% 52%,rgba(255,255,255,.6),transparent 35%),linear-gradient(90deg,transparent 49.92%,rgba(24,33,28,.08) 50%,transparent 50.08%);pointer-events:none}
.handoff-kicker{position:absolute;left:var(--pad);top:108px;font:400 8px/1 DM Mono,monospace;letter-spacing:.15em;text-transform:uppercase;opacity:.48}
.handoff-index{position:absolute;right:var(--pad);top:100px;min-width:150px;padding-top:9px;border-top:1px solid rgba(24,33,28,.24);text-align:right;font:400 8px/1.5 DM Mono,monospace;letter-spacing:.1em;text-transform:uppercase;opacity:.48}
.handoff-index b{display:block;font:300 28px/.9 Fraunces,serif;letter-spacing:-.05em;margin-bottom:7px}
.handoff-words{position:absolute;z-index:1;inset:0;display:flex;flex-direction:column;justify-content:center;gap:.02em;padding:4vh var(--pad);font:300 clamp(74px,11.8vw,184px)/.78 Fraunces,serif;letter-spacing:-.075em;pointer-events:none}
.handoff-words span:nth-child(1){align-self:flex-start}.handoff-words span:nth-child(2){align-self:center;font-style:italic}.handoff-words span:nth-child(3){align-self:flex-end}.handoff-words span{opacity:.88}
.handoff-halo{position:absolute;z-index:2;left:50%;top:52%;width:clamp(360px,43vw,660px);aspect-ratio:1;transform:translate(-50%,-50%);border:1px solid rgba(24,33,28,.18);border-radius:50%;pointer-events:none}
.handoff-halo:before,.handoff-halo:after{content:"";position:absolute;border:1px solid rgba(24,33,28,.12);border-radius:50%;inset:13%}.handoff-halo:after{inset:29%;border-style:dashed;animation:spin 24s linear infinite}.handoff-halo .orbit{position:absolute;inset:-8%;border:1px solid rgba(185,126,101,.22);border-radius:50%;transform:rotate(19deg) scaleY(.72)}.handoff-halo .axis{position:absolute;left:50%;top:-5%;bottom:-5%;width:1px;background:linear-gradient(transparent,rgba(24,33,28,.16),transparent)}
.handoff-caption{position:absolute;z-index:4;left:var(--pad);bottom:46px;width:min(360px,30vw);padding-top:13px;border-top:1px solid rgba(24,33,28,.23);font-size:11px;line-height:1.65;opacity:.62}.handoff-caption b{display:block;margin-bottom:8px;font:500 8px/1 DM Mono,monospace;letter-spacing:.12em;text-transform:uppercase}
.view[data-view="object"]>.page.paper{min-height:112svh}.view[data-view="object"]>.page.paper .visual{transition:opacity .28s linear}
'''
s=once(s,marker,css+'\n'+marker,'cinematic css')

# Hero + handoff markup.
start=s.index('<section class="hero" id="top">')
end=s.index('<section class="page paper">',start)
hero='''<section class="hero" id="top">
<img class="hero-clouds hero-bg" data-depth=".13" src="images/masck-hero-sky-ribbons-v1.webp" alt="" fetchpriority="high" />
<div class="hero-vignette"></div>
<div class="hero-copy" data-depth-copy>
<div class="eyebrow">Hands-free facial cleansing</div>
<h1><span>Less time.</span><span>More you.</span></h1>
<p>MASCK ONE is a contained facial-cleansing wearable engineered to deliver, move and recover cleansing fluid while your hands stay free.</p>
</div>
<div class="hero-meta"><b>01</b>Object / 01 of 03<br>form in motion</div>
<div class="band masck" data-depth=".25" aria-hidden="true"><div class="band-track"><span>MASCK <i>•</i> MASCK <i>•</i> MASCK <i>•</i> MASCK <i>•</i></span><span>MASCK <i>•</i> MASCK <i>•</i> MASCK <i>•</i> MASCK <i>•</i></span></div></div>
<img class="hero-person hero-subject" data-depth=".52" src="images/masck-hero-caucasian-mask-v1.webp" alt="Woman looking upward while wearing a MASCK ONE concept render" fetchpriority="high" />
<div class="band one" data-depth=".31" aria-hidden="true"><div class="band-track"><span>ONE <i>•</i> ONE <i>•</i> ONE <i>•</i> ONE <i>•</i> ONE <i>•</i></span><span>ONE <i>•</i> ONE <i>•</i> ONE <i>•</i> ONE <i>•</i> ONE <i>•</i></span></div></div>
<div class="hero-bottom"><span><div class="line"></div>Scroll / follow the object</span><span>MASCK ONE / 2026</span></div>
</section>
<div class="mask-journey" aria-hidden="true"><img src="https://masck-one.vercel.app/images/masck-one-product-angle.webp" alt="" /></div>
<section class="handoff-page" aria-label="Object System Proof overview"><div class="handoff-stage"><div class="handoff-kicker">One wearable / three layers of evidence</div><div class="handoff-index"><b>02</b>Object / system / proof</div><div class="handoff-words" aria-hidden="true"><span>Object.</span><span>System.</span><span>Proof.</span></div><div class="handoff-halo" aria-hidden="true"><span class="orbit"></span><span class="axis"></span></div><div class="handoff-caption"><b>The same object, followed downward</b>The product moves from appearance to architecture, then into the systems and evidence that make the object credible.</div></div></section>
'''
s=s[:start]+hero+s[end:]
s=once(s,'<div class="section-tag"><span>Object</span><b>02 / 02</b></div>','<div class="section-tag"><span>Object</span><b>03 / 03</b></div>','object tag')
s=once(s,'<div class="page-index">01 / Object / 02</div>','<div class="page-index">01 / Object / 03</div>','object index')
s=once(s,'The product reads as one quiet surface, but it is engineered as a stack:', 'The floating object resolves into a physical stack:', 'copy')

mobile_marker='@media(max-width:900px) and (prefers-reduced-motion:reduce)'
mobile='''@media(min-width:901px) and (max-width:1120px){.hero-subject{right:-5vw;height:106vh}.band{height:clamp(86px,9vw,112px)}.band span{font-size:clamp(50px,6.2vw,72px)}.handoff-words{font-size:clamp(72px,11.7vw,126px)}}
@media(max-width:900px){.hero-subject{right:-43vw;bottom:4vh;height:76vh;-webkit-mask-image:linear-gradient(90deg,transparent 0,#000 18%,#000 100%);mask-image:linear-gradient(90deg,transparent 0,#000 18%,#000 100%)}.hero-copy{top:11.2vh;z-index:10}.hero h1{max-width:80%;font-size:clamp(50px,14vw,72px)}.hero-copy p{max-width:66%}.band{left:-28vw;width:156vw;height:72px}.band span{font-size:46px}.band.masck{top:49%}.band.one{top:65%}.mask-journey{width:clamp(190px,58vw,300px)}.handoff-page{height:122svh}.handoff-stage{padding:80px 24px 45px}.handoff-kicker{left:24px;top:84px}.handoff-index{right:24px;top:80px;min-width:118px}.handoff-words{padding:7vh 22px 5vh;font-size:clamp(68px,22vw,112px);line-height:.8}.handoff-words span:nth-child(2){align-self:flex-start;margin-left:8vw}.handoff-words span:nth-child(3){align-self:flex-end}.handoff-halo{top:53%;width:min(82vw,480px)}.handoff-caption{left:24px;bottom:30px;width:min(72vw,330px);font-size:10px}}
'''
s=once(s,mobile_marker,mobile+mobile_marker,'mobile cinematic')
s=once(s,'.hero-clouds,.hero-person,.visual-stage{transform:none!important}', '.hero-clouds,.hero-person,.visual-stage,.mask-journey{transform:none!important}', 'reduced motion journey')

# Journey JS.
s=once(s,'const smooth=t=>t*t*(3-2*t);','const smooth=t=>t*t*(3-2*t);\n\nconst mix=(a,b,t)=>a+(b-a)*t;','mix')
s=once(s,"const navProgressFill=document.querySelector('.nav-progress-fill');", "const navProgressFill=document.querySelector('.nav-progress-fill');\n\nconst journey=document.querySelector('.mask-journey');\nconst heroSubject=document.querySelector('.hero-subject');\nconst handoff=document.querySelector('.handoff-page');\nconst objectPaper=document.querySelector('.view[data-view=\"object\"] > .page.paper');", 'journey refs')
s=once(s,'active=name;\nviews.forEach', "active=name;\nif(journey&&name!=='object')journey.style.opacity='0';\nviews.forEach", 'hide journey')
old='''if(active==='object'&&hero){
const p=Math.min(1,sy/Math.max(1,hero.offsetHeight));
heroLayers.forEach(el=>{
const d=+el.dataset.depth||0;
const x=mx*d*24,y=my*d*15+p*d*92;
if(el.classList.contains('band')){
const rot=el.classList.contains('masck')?-3.5:3.5;
el.style.transform=`translate3d(${x}px,${y*.18}px,0) rotate(${rot+mx*d*.65}deg)`}
else if(el.classList.contains('hero-clouds')){
el.style.transform=`translate3d(${x*.45}px,${y*.35}px,0) scale(${1.035+p*.05})`}
else{
const side=el.classList.contains('hero-male')?-1:1;
el.style.transform=`translate3d(${x+side*p*27}px,${y}px,0) scale(${1+p*.024})`}
}
);
if(heroCopy)heroCopy.style.transform=`translate3d(${mx*2.5}px,${-p*24+my*1.8}px,0)`}
'''
new='''if(active==='object'&&hero){
const p=Math.min(1,sy/Math.max(1,hero.offsetHeight));
heroLayers.forEach(el=>{
const d=+el.dataset.depth||0;
const x=mx*d*24,y=my*d*15+p*d*92;
if(el.classList.contains('band')){
const rot=el.classList.contains('masck')?-3.5:3.5;
el.style.transform=`translate3d(${x}px,${y*.15}px,0) rotate(${rot+mx*d*.65}deg)`}
else if(el.classList.contains('hero-clouds')){
el.style.transform=`translate3d(${x*.38}px,${y*.24}px,0) scale(${1.02+p*.045})`}
else if(el.classList.contains('hero-subject')){
el.style.transform=`translate3d(${x+p*18}px,${y*.62}px,0) scale(${1+p*.018})`}
}
);
if(heroCopy)heroCopy.style.transform=`translate3d(${mx*2.5}px,${-p*24+my*1.8}px,0)`;
if(journey&&handoff&&objectPaper){
const heroH=Math.max(1,hero.offsetHeight);const paperTop=objectPaper.offsetTop;
const detach=smooth(clamp((sy-heroH*.18)/(heroH*.68),0,1));const paperEntry=smooth(clamp((sy-(paperTop-innerHeight*.72))/(innerHeight*.9),0,1));const fadeOut=smooth(clamp((sy-(paperTop+innerHeight*.02))/(innerHeight*.5),0,1));const show=smooth(clamp((sy-heroH*.22)/(heroH*.28),0,1));
const sx=innerWidth*(desktop()?.735:.68),sy0=innerHeight*(desktop()?.46:.56),cx=innerWidth*.5,cy=innerHeight*.52,tx2=innerWidth*(desktop()?.72:.5),ty2=innerHeight*(desktop()?.49:.31);
const x=mix(mix(sx,cx,detach),tx2,paperEntry),y=mix(mix(sy0,cy,detach),ty2,paperEntry),scale=mix(mix(desktop()?.58:.72,1,detach),desktop()?.82:.76,paperEntry);
journey.style.opacity=String(show*(1-fadeOut));journey.style.transform=`translate3d(${x}px,${y}px,0) translate(-50%,-50%) scale(${scale}) rotate(${mix(-5,0,detach)+mix(0,4,paperEntry)}deg)`;
if(heroSubject)heroSubject.style.opacity=String(1-smooth(clamp((sy-heroH*.6)/(heroH*.34),0,1))*.72);
}
}else if(journey){journey.style.opacity='0'}
'''
s=once(s,old,new,'journey render')

# Decode staged image chunks.
parts=ROOT/'.site-build'
for out,names in {
    ROOT/'website/images/masck-hero-caucasian-mask-v1.webp':['hero-fg-1.b64','hero-fg-2.b64','hero-fg-3.b64'],
    ROOT/'website/images/masck-hero-sky-ribbons-v1.webp':['hero-bg-1.b64','hero-bg-2.b64'],
}.items():
    data=''.join((parts/n).read_text().strip() for n in names)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_bytes(base64.b64decode(data))

INDEX.write_text(s)
print('website/index.html',git_blob_sha(INDEX.read_bytes()))
