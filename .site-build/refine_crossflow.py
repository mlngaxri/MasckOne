from pathlib import Path
import hashlib

ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/'website/index.html'
EXPECTED='c20a2bee83ce8d1a6f33f62de148b8b5c6af40ea'

def blob_sha(data: bytes)->str:
    h=hashlib.sha1(); h.update(f'blob {len(data)}\0'.encode()); h.update(data); return h.hexdigest()

def once(s, old, new, label):
    n=s.count(old)
    if n!=1: raise RuntimeError(f'{label}: expected 1 match, got {n}')
    return s.replace(old,new,1)

raw=INDEX.read_bytes(); sha=blob_sha(raw); s=raw.decode()
if 'handoff-halo-stream' in s and '--stream-y' in s:
    print('crossflow refinement already applied'); raise SystemExit(0)
if sha!=EXPECTED: raise RuntimeError(f'unexpected website baseline {sha}')

# Make orbit typography a fixed stream whose vertical position is scroll-driven.
old='.mask-orbit-overlay{position:fixed;left:50%;top:52%;z-index:1110;width:clamp(600px,62vw,940px);aspect-ratio:1;transform:translate(-50%,-50%) rotate(-7deg) scaleY(.42);opacity:0;pointer-events:none;will-change:opacity;overflow:visible}'
new='.mask-orbit-overlay{--stream-y:118vh;position:fixed;left:50%;top:0;z-index:1110;width:clamp(600px,62vw,940px);aspect-ratio:1;transform:translate(-50%,-50%) translateY(var(--stream-y)) rotate(-7deg) scaleY(.42);opacity:0;pointer-events:none;will-change:opacity,transform;overflow:visible}'
s=once(s,old,new,'orbit stream css')

# Turn the halo into an independent fixed stream moving in the opposite direction.
old='.handoff-halo{position:absolute;z-index:2;left:50%;top:52%;width:clamp(430px,49vw,740px);height:clamp(230px,22vw,340px);transform:translate(-50%,-50%) rotate(-7deg);border:1px solid rgba(24,33,28,.18);border-radius:50%;pointer-events:none}'
new='.handoff-halo{--halo-y:122vh;position:fixed;z-index:1115;left:50%;top:0;width:clamp(430px,49vw,740px);height:clamp(230px,22vw,340px);transform:translate(-50%,-50%) translateY(var(--halo-y)) rotate(-7deg);border:1px solid rgba(24,33,28,.18);border-radius:50%;pointer-events:none;opacity:0;will-change:opacity,transform}'
s=once(s,old,new,'halo stream css')

# Mobile overrides should not pin either stream to a static viewport center.
s=once(s,'@media(max-width:900px){.mask-orbit-overlay{top:53%;width:min(128vw,650px)}', '@media(max-width:900px){.mask-orbit-overlay{width:min(128vw,650px)}', 'mobile orbit top')
s=once(s,'.handoff-halo{top:53%;width:min(82vw,480px)}', '.handoff-halo{width:min(82vw,480px)}', 'mobile halo top')

# Lift the halo out of the sticky handoff section so it can visibly cross section boundaries.
old='<div class="mask-orbit-overlay orbit-front" aria-hidden="true"><div class="mask-orbit-node" style="--delay:0s"><span>Architecture.</span></div><div class="mask-orbit-node" style="--delay:-6s"><span>Systems.</span></div><div class="mask-orbit-node" style="--delay:-12s"><span>Proof.</span></div></div>\n<section class="handoff-page" aria-label="Architecture Systems Proof overview"><div class="handoff-stage"><div class="handoff-index"><b>02</b>Architecture / systems / proof</div><div class="handoff-halo" aria-hidden="true"><span class="orbit"></span><span class="axis"></span></div><div class="handoff-caption">'
new='<div class="mask-orbit-overlay orbit-front" aria-hidden="true"><div class="mask-orbit-node" style="--delay:0s"><span>Architecture.</span></div><div class="mask-orbit-node" style="--delay:-6s"><span>Systems.</span></div><div class="mask-orbit-node" style="--delay:-12s"><span>Proof.</span></div></div>\n<div class="handoff-halo handoff-halo-stream" aria-hidden="true"><span class="orbit"></span><span class="axis"></span></div>\n<section class="handoff-page" aria-label="Architecture Systems Proof overview"><div class="handoff-stage"><div class="handoff-index"><b>02</b>Architecture / systems / proof</div><div class="handoff-caption">'
s=once(s,old,new,'move halo outside handoff')

# JS references + view cleanup.
s=once(s,"const orbitCopies=[...document.querySelectorAll('.mask-orbit-overlay')];", "const orbitCopies=[...document.querySelectorAll('.mask-orbit-overlay')];\nconst haloStream=document.querySelector('.handoff-halo-stream');", 'halo js ref')
s=once(s,"if(name!=='object')orbitCopies.forEach(el=>el.style.opacity='0');", "if(name!=='object'){orbitCopies.forEach(el=>el.style.opacity='0');if(haloStream)haloStream.style.opacity='0'}", 'hide streams on view switch')

# Replace the simple fade with opposing vertical travel across the three Object screens.
old='''const orbitReveal=smooth(clamp((detach-.86)/.12,0,1))*(1-smooth(clamp((paperEntry-.55)/.32,0,1)));\norbitCopies.forEach(el=>el.style.opacity=String(orbitReveal));\nconst sx=innerWidth*(desktop()?.735:.68),sy0=innerHeight*(desktop()?.46:.56),cx=innerWidth*.5,cy=innerHeight*.52,tx2=innerWidth*(desktop()?.72:.5),ty2=innerHeight*(desktop()?.49:.31);'''
new='''const handoffTop=handoff.offsetTop;\nconst textEnter=smooth(clamp((sy-heroH*.72)/(innerHeight*.72),0,1));\nconst textExit=smooth(clamp((sy-(paperTop-innerHeight*.92))/(innerHeight*.96),0,1));\nconst textY=mix(mix(innerHeight*1.22,innerHeight*.52,textEnter),innerHeight*1.26,textExit);\nconst textOpacity=smooth(clamp((textEnter-.05)/.22,0,1))*(1-smooth(clamp((textExit-.78)/.2,0,1)));\norbitCopies.forEach(el=>{el.style.opacity=String(textOpacity);el.style.setProperty('--stream-y',`${textY}px`)});\n\nconst haloEnter=smooth(clamp((sy-(handoffTop-innerHeight*.12))/(innerHeight*.76),0,1));\nconst haloExit=smooth(clamp((sy-(paperTop-innerHeight*1.02))/(innerHeight*.9),0,1));\nconst haloY=mix(mix(innerHeight*1.22,innerHeight*.52,haloEnter),-innerHeight*.24,haloExit);\nconst haloOpacity=smooth(clamp((haloEnter-.04)/.2,0,1))*(1-smooth(clamp((haloExit-.82)/.16,0,1)));\nif(haloStream){haloStream.style.opacity=String(haloOpacity);haloStream.style.setProperty('--halo-y',`${haloY}px`)}\nconst sx=innerWidth*(desktop()?.735:.68),sy0=innerHeight*(desktop()?.46:.56),cx=innerWidth*.5,cy=innerHeight*.52,tx2=innerWidth*(desktop()?.72:.5),ty2=innerHeight*(desktop()?.49:.31);'''
s=once(s,old,new,'opposing stream motion')

s=once(s,"}else if(journey){journey.style.opacity='0';orbitCopies.forEach(el=>el.style.opacity='0')}", "}else if(journey){journey.style.opacity='0';orbitCopies.forEach(el=>el.style.opacity='0');if(haloStream)haloStream.style.opacity='0'}", 'stream fallback hide')

INDEX.write_text(s)
print('refined', blob_sha(INDEX.read_bytes()))
