from pathlib import Path
import hashlib,re

ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/'website/index.html'
EXPECTED='616ce6a80e83f8f023b027eb35ef3d4b9b9fe1ca'

def blob_sha(data:bytes)->str:
    h=hashlib.sha1(); h.update(f'blob {len(data)}\0'.encode()); h.update(data); return h.hexdigest()

def once(s,old,new,label):
    n=s.count(old)
    if n!=1: raise RuntimeError(f'{label}: expected 1 match, got {n}')
    return s.replace(old,new,1)

raw=INDEX.read_bytes(); sha=blob_sha(raw)
if sha!=EXPECTED:
    raise RuntimeError(f'unexpected website baseline {sha}')
s=raw.decode()

# Navbar: consistent naming, earthy progress, center-out reveal only once page two arrives.
s=once(s,'<button class="active" type="button" data-view-target="object" aria-pressed="true">Object</button>','<button class="active" type="button" data-view-target="object" aria-pressed="true">Architecture</button>','architecture nav label')
s=once(s,'<button type="button" data-view-target="system" aria-pressed="false">System</button>','<button type="button" data-view-target="system" aria-pressed="false">Systems</button>','systems nav label')
s=once(s,'<section class="view active" data-view="object" aria-label="Object section">','<section class="view active" data-view="object" aria-label="Architecture section">','architecture aria label')

css_marker='/* Object cleanup + navbar progress clipping */\n.header{overflow:hidden}\n.nav-progress{left:1px;right:1px;bottom:1px;height:3px;border-radius:0 0 999px 999px}\n'
css_new='''/* Feature-stage navbar */
.header{overflow:hidden;opacity:0;pointer-events:none;clip-path:inset(0 50% 0 50% round 999px);transform:translateX(-50%) scaleX(.08);transition:clip-path .72s cubic-bezier(.22,.78,.18,1),transform .72s cubic-bezier(.22,.78,.18,1),opacity .22s ease}
.header>*{opacity:0;transition:opacity .24s ease .18s}
.header.is-visible{opacity:1;pointer-events:auto;clip-path:inset(0 0 0 0 round 999px);transform:translateX(-50%) scaleX(1)}
.header.is-visible>*{opacity:1}
.nav-progress{left:1px;right:1px;bottom:1px;height:3px;border-radius:0 0 999px 999px}
.nav-progress-fill{background:#788970;box-shadow:0 0 10px rgba(120,137,112,.34)}

/* Seamless campaign ribbons */
.band-track{display:flex;flex:none;width:max-content;min-width:0;gap:0;animation:marquee 16s linear infinite;will-change:transform}
.band-track>span{display:block;flex:0 0 auto;white-space:nowrap;margin:0;padding:0}
@keyframes marquee{from{transform:translate3d(0,0,0)}to{transform:translate3d(-50%,0,0)}}
'''
s=once(s,css_marker,css_new,'feature navbar css')

# Remove earlier clay/blue progress declaration by overriding it cleanly above; keep thickness/mask.

# Make each marquee half substantially wider than the viewport so the -50% loop can never expose track background.
masck='MASCK <i>•</i> '
one='ONE <i>•</i> '
masck_seq=(masck*16)+'MASCK'
one_seq=(one*22)+'ONE'
old_m='<div class="band masck" data-depth=".25" aria-hidden="true"><div class="band-track"><span>MASCK <i>•</i> MASCK <i>•</i> MASCK <i>•</i> MASCK <i>•</i></span><span>MASCK <i>•</i> MASCK <i>•</i> MASCK <i>•</i> MASCK <i>•</i></span></div></div>'
new_m=f'<div class="band masck" data-depth=".25" aria-hidden="true"><div class="band-track"><span>{masck_seq}</span><span>{masck_seq}</span></div></div>'
s=once(s,old_m,new_m,'seamless masck ribbon')
old_o='<div class="band one" data-depth=".31" aria-hidden="true"><div class="band-track"><span>ONE <i>•</i> ONE <i>•</i> ONE <i>•</i> ONE <i>•</i> ONE <i>•</i></span><span>ONE <i>•</i> ONE <i>•</i> ONE <i>•</i> ONE <i>•</i> ONE <i>•</i></span></div></div>'
new_o=f'<div class="band one" data-depth=".31" aria-hidden="true"><div class="band-track"><span>{one_seq}</span><span>{one_seq}</span></div></div>'
s=once(s,old_o,new_o,'seamless one ribbon')

# Second screen becomes the permanent feature stage: no index and future-facing feature copy.
old_handoff='<section class="handoff-page" aria-label="Architecture Systems Proof overview"><div class="handoff-stage"><div class="handoff-index"><b>02</b>Architecture / systems / proof</div><div class="handoff-caption"><b>The same object, followed downward.</b><span>As you scroll, MASCK ONE moves from its exterior form into the architecture, systems and proof behind the product.</span></div></div></section>'
new_handoff='<section class="handoff-page" aria-label="Architecture Systems Proof overview"><div class="handoff-stage"><div class="handoff-caption"><b>Architecture. Systems. Proof.</b><span>Explore what MASCK ONE is, how it works, and the evidence behind it.</span></div></div></section>'
s=once(s,old_handoff,new_handoff,'feature-stage copy')

# Remove the old third Object page entirely.
pat=r'\n<section class="page paper">.*?</section>\n</section>\n\n<section class="view" data-view="system" aria-label="System section">'
repl='\n</section>\n\n<section class="view" data-view="system" aria-label="System section">'
s,n=re.subn(pat,repl,s,count=1,flags=re.S)
if n!=1: raise RuntimeError(f'remove third Object page: expected 1 match, got {n}')

# JS references + navbar reveal.
s=once(s,"const navProgressFill=document.querySelector('.nav-progress-fill');","const navProgressFill=document.querySelector('.nav-progress-fill');\nconst header=document.querySelector('.header');",'header js ref')
s=once(s,'const objectPaper=document.querySelector(\'.view[data-view="object"] > .page.paper\');\n','', 'remove objectPaper ref')

old_progress='''function updateNavProgress(position=scrollY){
const current=document.querySelector('.view.active');
if(!current||!navProgressFill)return;
const max=Math.max(0,current.scrollHeight-innerHeight);
const progress=max>0?clamp(position/max,0,1):0;
navProgressFill.style.transform=`scaleX(${progress})`;
}

function jumpToTop(){
if(lenis)lenis.scrollTo(0,{immediate:true,force:true});
else window.scrollTo(0,0);
}
'''
new_progress='''function updateHeaderVisibility(position=scrollY){
if(!header)return;
const threshold=handoff?Math.max(0,handoff.offsetTop-24):innerHeight;
const visible=active!=='object'||position>=threshold;
header.classList.toggle('is-visible',visible);
}

function updateNavProgress(position=scrollY){
const current=document.querySelector('.view.active');
if(!current||!navProgressFill)return;
const max=Math.max(0,current.scrollHeight-innerHeight);
const progress=max>0?clamp(position/max,0,1):0;
navProgressFill.style.transform=`scaleX(${progress})`;
updateHeaderVisibility(position);
}

function jumpToPosition(y=0){
if(lenis)lenis.scrollTo(y,{immediate:true,force:true});
else window.scrollTo(0,y);
}
'''
s=once(s,old_progress,new_progress,'navbar reveal js')

old_set='''function setActive(name){
active=name;
if(journey&&name!=='object')journey.style.opacity='0';
if(name!=='object'){orbitCopies.forEach(el=>el.style.opacity='0');if(haloStream)haloStream.style.opacity='0'}
views.forEach(v=>v.classList.toggle('active',v.dataset.view===name));
nav.forEach(b=>{
const isActive=b.dataset.viewTarget===name;
b.classList.toggle('active',isActive);
b.setAttribute('aria-pressed',String(isActive))}
);
jumpToTop();
sy=0;
if(lenis)lenis.resize();
updateNavProgress(0);
requestFrame();
'''
new_set='''function setActive(name,featureAnchor=false){
active=name;
if(journey&&name!=='object')journey.style.opacity='0';
if(name!=='object'){orbitCopies.forEach(el=>el.style.opacity='0');if(haloStream)haloStream.style.opacity='0'}
views.forEach(v=>v.classList.toggle('active',v.dataset.view===name));
nav.forEach(b=>{
const isActive=b.dataset.viewTarget===name;
b.classList.toggle('active',isActive);
b.setAttribute('aria-pressed',String(isActive))}
);
const target=name==='object'&&featureAnchor&&handoff?handoff.offsetTop:0;
jumpToPosition(target);
sy=target;
if(lenis)lenis.resize();
updateNavProgress(target);
requestFrame();
'''
s=once(s,old_set,new_set,'setActive feature anchor')

s=once(s,"if(name===active){\nif(lenis)lenis.scrollTo(0,{duration:1.05});\nelse window.scrollTo({top:0,behavior:'smooth'});\nreturn}","if(name===active){\nconst target=name==='object'&&handoff?handoff.offsetTop:0;\nif(lenis)lenis.scrollTo(target,{duration:1.05});\nelse window.scrollTo({top:target,behavior:'smooth'});\nreturn}",'active nav target')
s=once(s,'setActive(name);\nswitching=false;','setActive(name,name===\'object\');\nswitching=false;','mobile feature anchor')
s=once(s,'setActive(name);\nstaircase.classList.add(\'exit\');','setActive(name,name===\'object\');\nstaircase.classList.add(\'exit\');','desktop feature anchor')

# Rebuild the Object journey now that there is no third page. Mask settles on page two; orbit exits downward, halo exits upward.
old_block='''if(journey&&handoff&&objectPaper){
const heroH=Math.max(1,hero.offsetHeight);const paperTop=objectPaper.offsetTop;
const detach=smooth(clamp((sy-heroH*.18)/(heroH*.68),0,1));const paperEntry=smooth(clamp((sy-(paperTop-innerHeight*.72))/(innerHeight*.9),0,1));const fadeOut=smooth(clamp((sy-(paperTop+innerHeight*.02))/(innerHeight*.5),0,1));const show=smooth(clamp((sy-heroH*.22)/(heroH*.28),0,1));
const handoffTop=handoff.offsetTop;
const textEnter=smooth(clamp((sy-heroH*.72)/(innerHeight*.72),0,1));
const textExit=smooth(clamp((sy-(paperTop-innerHeight*.92))/(innerHeight*.96),0,1));
const textY=mix(mix(innerHeight*1.22,innerHeight*.52,textEnter),innerHeight*1.26,textExit);
const textOpacity=smooth(clamp((textEnter-.05)/.22,0,1))*(1-smooth(clamp((textExit-.78)/.2,0,1)));
orbitCopies.forEach(el=>{el.style.opacity=String(textOpacity);el.style.setProperty('--stream-y',`${textY}px`)});

const haloEnter=smooth(clamp((sy-(handoffTop-innerHeight*.12))/(innerHeight*.76),0,1));
const haloExit=smooth(clamp((sy-(paperTop-innerHeight*1.02))/(innerHeight*.9),0,1));
const haloY=mix(mix(innerHeight*1.22,innerHeight*.52,haloEnter),-innerHeight*.24,haloExit);
const haloOpacity=smooth(clamp((haloEnter-.04)/.2,0,1))*(1-smooth(clamp((haloExit-.82)/.16,0,1)));
if(haloStream){haloStream.style.opacity=String(haloOpacity);haloStream.style.setProperty('--halo-y',`${haloY}px`)}
const sx=innerWidth*(desktop()?.735:.68),sy0=innerHeight*(desktop()?.46:.56),cx=innerWidth*.5,cy=innerHeight*.52,tx2=innerWidth*(desktop()?.72:.5),ty2=innerHeight*(desktop()?.49:.31);
const x=mix(mix(sx,cx,detach),tx2,paperEntry),y=mix(mix(sy0,cy,detach),ty2,paperEntry),scale=mix(mix(desktop()?.58:.72,1,detach),desktop()?.82:.76,paperEntry);
journey.style.opacity=String(show*(1-fadeOut));journey.style.transform=`translate3d(${x}px,${y}px,0) translate(-50%,-50%) scale(${scale}) rotate(${mix(-5,0,detach)+mix(0,4,paperEntry)}deg)`;
if(heroSubject)heroSubject.style.opacity=String(1-smooth(clamp((sy-heroH*.6)/(heroH*.34),0,1))*.72);
}
'''
new_block='''if(journey&&handoff){
const heroH=Math.max(1,hero.offsetHeight);const handoffTop=handoff.offsetTop;const handoffEnd=handoffTop+handoff.offsetHeight;
const detach=smooth(clamp((sy-heroH*.18)/(heroH*.68),0,1));const show=smooth(clamp((sy-heroH*.22)/(heroH*.28),0,1));
const textEnter=smooth(clamp((sy-heroH*.72)/(innerHeight*.72),0,1));
const textExit=smooth(clamp((sy-(handoffEnd-innerHeight*.56))/(innerHeight*.5),0,1));
const textY=mix(mix(innerHeight*1.22,innerHeight*.52,textEnter),innerHeight*1.28,textExit);
const textOpacity=smooth(clamp((textEnter-.05)/.22,0,1))*(1-smooth(clamp((textExit-.76)/.2,0,1)));
orbitCopies.forEach(el=>{el.style.opacity=String(textOpacity);el.style.setProperty('--stream-y',`${textY}px`)});

const haloEnter=smooth(clamp((sy-(handoffTop-innerHeight*.08))/(innerHeight*.72),0,1));
const haloExit=smooth(clamp((sy-(handoffEnd-innerHeight*.72))/(innerHeight*.58),0,1));
const haloY=mix(mix(innerHeight*1.22,innerHeight*.52,haloEnter),-innerHeight*.24,haloExit);
const haloOpacity=smooth(clamp((haloEnter-.04)/.2,0,1))*(1-smooth(clamp((haloExit-.8)/.17,0,1)));
if(haloStream){haloStream.style.opacity=String(haloOpacity);haloStream.style.setProperty('--halo-y',`${haloY}px`)}
const sx=innerWidth*(desktop()?.735:.68),sy0=innerHeight*(desktop()?.46:.56),cx=innerWidth*.5,cy=innerHeight*.52;
const x=mix(sx,cx,detach),y=mix(sy0,cy,detach),scale=mix(desktop()?.58:.72,1,detach);
journey.style.opacity=String(show);journey.style.transform=`translate3d(${x}px,${y}px,0) translate(-50%,-50%) scale(${scale}) rotate(${mix(-5,0,detach)}deg)`;
if(heroSubject)heroSubject.style.opacity=String(1-smooth(clamp((sy-heroH*.6)/(heroH*.34),0,1))*.72);
}
'''
s=once(s,old_block,new_block,'two-page Object journey')

# Initial header state must be correct without requiring a scroll event.
s=once(s,'clearDesktopResidue();\nupdateNavProgress();\nrequestFrame();','clearDesktopResidue();\nupdateHeaderVisibility();\nupdateNavProgress();\nrequestFrame();','initial header state')

INDEX.write_text(s)
print('refined',blob_sha(INDEX.read_bytes()))
