from pathlib import Path
import hashlib

ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/'website/index.html'
EXPECTED='6d204b44b8ee0e6546ac61db922de8244667ce7b'

def git_blob_sha(data: bytes)->str:
    h=hashlib.sha1(); h.update(f'blob {len(data)}\0'.encode()); h.update(data); return h.hexdigest()

def once(s, old, new, label):
    n=s.count(old)
    if n!=1:
        raise RuntimeError(f'{label}: expected 1 match, got {n}')
    return s.replace(old,new,1)

raw=INDEX.read_bytes()
sha=git_blob_sha(raw)
s=raw.decode()
if 'handoff-orbit-copy' in s and 'Hands-free facial cleansing' not in s:
    print('orbit refinement already applied')
    raise SystemExit(0)
if sha!=EXPECTED:
    raise RuntimeError(f'unexpected website baseline {sha}')

# Landing: remove eyebrow and rebalance headline slightly lower.
s=once(s,'<div class="eyebrow">Hands-free facial cleansing</div>\n','', 'remove hero eyebrow')
s=once(s,'.hero-copy{z-index:8;top:14.2vh;width:min(450px,34vw)}', '.hero-copy{z-index:8;top:16vh;width:min(450px,34vw)}', 'rebalance hero copy')

# Handoff: replace large static words with a real orbital label system and strengthen caption readability.
old_css='''.handoff-words{position:absolute;z-index:1;inset:0;display:flex;flex-direction:column;justify-content:center;gap:.02em;padding:4vh var(--pad);font:300 clamp(74px,11.8vw,184px)/.78 Fraunces,serif;letter-spacing:-.075em;pointer-events:none}\n.handoff-words span:nth-child(1){align-self:flex-start}.handoff-words span:nth-child(2){align-self:center;font-style:italic}.handoff-words span:nth-child(3){align-self:flex-end}.handoff-words span{opacity:.88}\n'''
new_css='''.handoff-orbit-copy{position:absolute;z-index:3;left:50%;top:52%;width:clamp(430px,50vw,760px);aspect-ratio:1;transform:translate(-50%,-50%);opacity:0;pointer-events:none;will-change:opacity}\n.handoff-orbit-node{--delay:0s;position:absolute;inset:0;animation:orbitLabelSpin 18s linear infinite;animation-delay:var(--delay)}\n.handoff-orbit-node span{position:absolute;left:50%;top:-1%;padding:.18em .4em;border:1px solid rgba(24,33,28,.12);border-radius:999px;background:rgba(246,241,232,.68);backdrop-filter:blur(10px);white-space:nowrap;font:300 clamp(25px,3.2vw,48px)/1 Fraunces,serif;letter-spacing:-.055em;box-shadow:0 10px 32px rgba(24,33,28,.055);transform:translate(-50%,-50%);animation:orbitLabelCounter 18s linear infinite;animation-delay:var(--delay)}\n@keyframes orbitLabelSpin{to{transform:rotate(360deg)}}\n@keyframes orbitLabelCounter{to{transform:translate(-50%,-50%) rotate(-360deg)}}\n'''
s=once(s,old_css,new_css,'replace static handoff words css')
old_caption='.handoff-caption{position:absolute;z-index:4;left:var(--pad);bottom:46px;width:min(360px,30vw);padding-top:13px;border-top:1px solid rgba(24,33,28,.23);font-size:11px;line-height:1.65;opacity:.62}.handoff-caption b{display:block;margin-bottom:8px;font:500 8px/1 DM Mono,monospace;letter-spacing:.12em;text-transform:uppercase}'
new_caption='.handoff-caption{position:absolute;z-index:4;left:var(--pad);bottom:42px;width:min(455px,37vw);padding:16px 18px 17px;border:1px solid rgba(24,33,28,.14);border-radius:14px;background:rgba(247,247,242,.68);backdrop-filter:blur(14px);font-size:12.5px;line-height:1.7;letter-spacing:-.01em;opacity:.88;box-shadow:0 14px 36px rgba(24,33,28,.055)}.handoff-caption b{display:block;margin-bottom:8px;font:300 21px/1.05 Fraunces,serif;letter-spacing:-.035em}.handoff-caption span{display:block;max-width:390px;opacity:.72}'
s=once(s,old_caption,new_caption,'clarify handoff caption')

# Mobile orbital geometry and clearer caption.
mobile_marker='@media(max-width:900px) and (prefers-reduced-motion:reduce)'
mobile_override='''@media(max-width:900px){.handoff-orbit-copy{top:53%;width:min(88vw,520px)}.handoff-orbit-node span{font-size:clamp(22px,7.5vw,34px);padding:.2em .42em}.handoff-caption{left:24px;bottom:28px;width:min(calc(100vw - 48px),390px);padding:14px 15px 15px;font-size:11px}.handoff-caption b{font-size:18px}}\n'''
s=once(s,mobile_marker,mobile_override+mobile_marker,'mobile orbit styles')

old_markup='<section class="handoff-page" aria-label="Object System Proof overview"><div class="handoff-stage"><div class="handoff-kicker">One wearable / three layers of evidence</div><div class="handoff-index"><b>02</b>Object / system / proof</div><div class="handoff-words" aria-hidden="true"><span>Object.</span><span>System.</span><span>Proof.</span></div><div class="handoff-halo" aria-hidden="true"><span class="orbit"></span><span class="axis"></span></div><div class="handoff-caption"><b>The same object, followed downward</b>The product moves from appearance to architecture, then into the systems and evidence that make the object credible.</div></div></section>'
new_markup='<section class="handoff-page" aria-label="Object System Proof overview"><div class="handoff-stage"><div class="handoff-index"><b>02</b>Object / system / proof</div><div class="handoff-orbit-copy" aria-hidden="true"><div class="handoff-orbit-node" style="--delay:0s"><span>Object.</span></div><div class="handoff-orbit-node" style="--delay:-6s"><span>System.</span></div><div class="handoff-orbit-node" style="--delay:-12s"><span>Proof.</span></div></div><div class="handoff-halo" aria-hidden="true"><span class="orbit"></span><span class="axis"></span></div><div class="handoff-caption"><b>The same object, followed downward.</b><span>As you scroll, MASCK ONE moves from its exterior form into the architecture, systems and evidence behind the product.</span></div></div></section>'
s=once(s,old_markup,new_markup,'replace handoff markup')

# JS: reveal orbital labels only after the travelling mask has reached center.
s=once(s,'const objectPaper=document.querySelector(\'.view[data-view="object"] > .page.paper\');', 'const objectPaper=document.querySelector(\'.view[data-view="object"] > .page.paper\');\nconst orbitCopy=document.querySelector(\'.handoff-orbit-copy\');', 'orbit js ref')
s=once(s,"if(journey&&name!=='object')journey.style.opacity='0';", "if(journey&&name!=='object')journey.style.opacity='0';\nif(orbitCopy&&name!=='object')orbitCopy.style.opacity='0';", 'hide orbit on view switch')
old_motion='''const detach=smooth(clamp((sy-heroH*.18)/(heroH*.68),0,1));const paperEntry=smooth(clamp((sy-(paperTop-innerHeight*.72))/(innerHeight*.9),0,1));const fadeOut=smooth(clamp((sy-(paperTop+innerHeight*.02))/(innerHeight*.5),0,1));const show=smooth(clamp((sy-heroH*.22)/(heroH*.28),0,1));\nconst sx=innerWidth*(desktop()?.735:.68),sy0=innerHeight*(desktop()?.46:.56),cx=innerWidth*.5,cy=innerHeight*.52,tx2=innerWidth*(desktop()?.72:.5),ty2=innerHeight*(desktop()?.49:.31);\n'''
new_motion='''const detach=smooth(clamp((sy-heroH*.18)/(heroH*.68),0,1));const paperEntry=smooth(clamp((sy-(paperTop-innerHeight*.72))/(innerHeight*.9),0,1));const fadeOut=smooth(clamp((sy-(paperTop+innerHeight*.02))/(innerHeight*.5),0,1));const show=smooth(clamp((sy-heroH*.22)/(heroH*.28),0,1));\nconst orbitReveal=smooth(clamp((detach-.86)/.12,0,1))*(1-smooth(clamp((paperEntry-.55)/.32,0,1)));\nif(orbitCopy)orbitCopy.style.opacity=String(orbitReveal);\nconst sx=innerWidth*(desktop()?.735:.68),sy0=innerHeight*(desktop()?.46:.56),cx=innerWidth*.5,cy=innerHeight*.52,tx2=innerWidth*(desktop()?.72:.5),ty2=innerHeight*(desktop()?.49:.31);\n'''
s=once(s,old_motion,new_motion,'orbit reveal timing')
s=once(s,"}else if(journey){journey.style.opacity='0'}", "}else if(journey){journey.style.opacity='0';if(orbitCopy)orbitCopy.style.opacity='0'}", 'orbit fallback hide')

INDEX.write_text(s)
print('refined', git_blob_sha(INDEX.read_bytes()))
