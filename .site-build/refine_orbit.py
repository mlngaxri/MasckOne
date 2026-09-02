from pathlib import Path
import hashlib

ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/'website/index.html'
EXPECTED='86773d3517c61f70e4b568297ed44a2d249fdef3'

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
if 'mask-orbit-overlay orbit-front' in s and 'Engineering development' not in s:
    print('elliptical orbit refinement already applied')
    raise SystemExit(0)
if sha!=EXPECTED:
    raise RuntimeError(f'unexpected website baseline {sha}')

# Navbar: remove status, make progress part of the lower edge, and give the border a subtle animated shader.
old_header='.header{position:fixed;z-index:1400;top:20px;left:50%;transform:translateX(-50%);width:min(92vw,1140px);height:var(--nav-h);padding:0 9px 0 20px;display:grid;grid-template-columns:1fr auto 1fr;align-items:center;border:1px solid rgba(255,255,255,.64);border-radius:999px;background:rgba(248,250,248,.74);backdrop-filter:blur(24px) saturate(1.14);box-shadow:0 13px 40px rgba(24,33,28,.065),inset 0 1px 0 rgba(255,255,255,.34)}'
new_header='.header{position:fixed;z-index:1400;top:20px;left:50%;transform:translateX(-50%);width:min(92vw,1140px);height:var(--nav-h);padding:0 9px 0 20px;display:grid;grid-template-columns:1fr auto 1fr;align-items:center;border:1px solid transparent;border-radius:999px;background:linear-gradient(rgba(248,250,248,.78),rgba(248,250,248,.72)) padding-box,linear-gradient(112deg,rgba(255,255,255,.96),rgba(185,126,101,.58),rgba(142,174,181,.58),rgba(198,207,185,.7),rgba(255,255,255,.96)) border-box;background-size:100% 100%,240% 100%;background-position:0 0,0% 50%;backdrop-filter:blur(24px) saturate(1.14);box-shadow:0 13px 40px rgba(24,33,28,.065),inset 0 1px 0 rgba(255,255,255,.34);animation:navShader 11s ease-in-out infinite alternate}'
s=once(s,old_header,new_header,'navbar shader')
s=once(s,'.status-chip{justify-self:end;display:flex;align-items:center;gap:8px;font:400 9px/1 DM Mono,monospace;letter-spacing:.08em;text-transform:uppercase;opacity:.62}\n.status-chip:before{content:"";width:6px;height:6px;border-radius:50%;background:#738269;box-shadow:0 0 0 5px rgba(115,130,105,.1)}\n','', 'remove status styles')
s=once(s,'.nav-progress{position:absolute;left:22px;right:22px;bottom:4px;height:1px;overflow:hidden;border-radius:999px;background:rgba(24,33,28,.095);pointer-events:none}\n.nav-progress-fill{position:absolute;inset:0;background:rgba(185,126,101,.9);transform:scaleX(0);transform-origin:left center;will-change:transform;box-shadow:0 0 7px rgba(185,126,101,.22)}', '.nav-progress{position:absolute;z-index:3;left:0;right:0;bottom:0;height:3px;overflow:hidden;border-radius:0 0 999px 999px;background:rgba(24,33,28,.085);pointer-events:none}\n.nav-progress-fill{position:absolute;inset:0;background:linear-gradient(90deg,#b97e65 0%,#d9b19d 42%,#8faeb4 72%,#9eaa8d 100%);transform:scaleX(0);transform-origin:left center;will-change:transform;box-shadow:0 0 10px rgba(185,126,101,.34)}\n@keyframes navShader{to{background-position:0 0,100% 50%}}', 'navbar progress edge')
s=once(s,'<div class="status-chip">Engineering development</div>\n','', 'remove status markup')

# Orbit: replace circular card labels with a perspective ellipse and split it into back/front layers around the fixed mask.
old_orbit='''.handoff-orbit-copy{position:absolute;z-index:3;left:50%;top:52%;width:clamp(430px,50vw,760px);aspect-ratio:1;transform:translate(-50%,-50%);opacity:0;pointer-events:none;will-change:opacity}\n.handoff-orbit-node{--delay:0s;position:absolute;inset:0;animation:orbitLabelSpin 18s linear infinite;animation-delay:var(--delay)}\n.handoff-orbit-node span{position:absolute;left:50%;top:-1%;padding:.18em .4em;border:1px solid rgba(24,33,28,.12);border-radius:999px;background:rgba(246,241,232,.68);backdrop-filter:blur(10px);white-space:nowrap;font:300 clamp(25px,3.2vw,48px)/1 Fraunces,serif;letter-spacing:-.055em;box-shadow:0 10px 32px rgba(24,33,28,.055);transform:translate(-50%,-50%);animation:orbitLabelCounter 18s linear infinite;animation-delay:var(--delay)}\n@keyframes orbitLabelSpin{to{transform:rotate(360deg)}}\n@keyframes orbitLabelCounter{to{transform:translate(-50%,-50%) rotate(-360deg)}}\n'''
new_orbit='''.mask-orbit-overlay{position:fixed;left:50%;top:52%;z-index:1110;width:clamp(600px,62vw,940px);aspect-ratio:1;transform:translate(-50%,-50%) rotate(-7deg) scaleY(.42);opacity:0;pointer-events:none;will-change:opacity;overflow:visible}\n.mask-orbit-overlay.orbit-back{clip-path:inset(-24% -30% 50% -30%)}\n.mask-orbit-overlay.orbit-front{z-index:1130;clip-path:inset(50% -30% -24% -30%)}\n.mask-orbit-node{--delay:0s;position:absolute;inset:0;animation:orbitEllipseSpin 18s linear infinite;animation-delay:var(--delay)}\n.mask-orbit-node span{position:absolute;left:50%;top:0;white-space:nowrap;font:300 clamp(42px,4.7vw,76px)/.9 Fraunces,serif;letter-spacing:-.065em;color:rgba(24,33,28,.94);text-shadow:0 8px 28px rgba(246,241,232,.72);transform:translate(-50%,-50%) rotate(7deg) scaleY(2.38095);animation:orbitEllipseCounter 18s linear infinite;animation-delay:var(--delay)}\n@keyframes orbitEllipseSpin{to{transform:rotate(360deg)}}\n@keyframes orbitEllipseCounter{to{transform:translate(-50%,-50%) rotate(-353deg) scaleY(2.38095)}}\n'''
s=once(s,old_orbit,new_orbit,'elliptical orbit css')

old_halo='.handoff-halo{position:absolute;z-index:2;left:50%;top:52%;width:clamp(360px,43vw,660px);aspect-ratio:1;transform:translate(-50%,-50%);border:1px solid rgba(24,33,28,.18);border-radius:50%;pointer-events:none}'
new_halo='.handoff-halo{position:absolute;z-index:2;left:50%;top:52%;width:clamp(430px,49vw,740px);height:clamp(230px,22vw,340px);transform:translate(-50%,-50%) rotate(-7deg);border:1px solid rgba(24,33,28,.18);border-radius:50%;pointer-events:none}'
s=once(s,old_halo,new_halo,'elliptical halo')

old_caption='.handoff-caption{position:absolute;z-index:4;left:var(--pad);bottom:42px;width:min(455px,37vw);padding:16px 18px 17px;border:1px solid rgba(24,33,28,.14);border-radius:14px;background:rgba(247,247,242,.68);backdrop-filter:blur(14px);font-size:12.5px;line-height:1.7;letter-spacing:-.01em;opacity:.88;box-shadow:0 14px 36px rgba(24,33,28,.055)}.handoff-caption b{display:block;margin-bottom:8px;font:300 21px/1.05 Fraunces,serif;letter-spacing:-.035em}.handoff-caption span{display:block;max-width:390px;opacity:.72}'
new_caption='.handoff-caption{position:absolute;z-index:4;left:var(--pad);bottom:42px;width:min(520px,42vw);padding:0;border:0;background:none;backdrop-filter:none;box-shadow:none;font-size:12.5px;line-height:1.72;letter-spacing:-.01em;opacity:1}.handoff-caption:before{content:"";display:block;width:54px;height:1px;margin-bottom:14px;background:linear-gradient(90deg,var(--clay),rgba(24,33,28,.18))}.handoff-caption b{display:block;margin-bottom:9px;font:300 clamp(23px,2vw,31px)/1 Fraunces,serif;letter-spacing:-.045em}.handoff-caption span{display:block;max-width:430px;opacity:.66}'
s=once(s,old_caption,new_caption,'remove caption card')

old_mobile='@media(max-width:900px){.handoff-orbit-copy{top:53%;width:min(88vw,520px)}.handoff-orbit-node span{font-size:clamp(22px,7.5vw,34px);padding:.2em .42em}.handoff-caption{left:24px;bottom:28px;width:min(calc(100vw - 48px),390px);padding:14px 15px 15px;font-size:11px}.handoff-caption b{font-size:18px}}'
new_mobile='@media(max-width:900px){.mask-orbit-overlay{top:53%;width:min(128vw,650px)}.mask-orbit-node span{font-size:clamp(30px,9vw,44px)}.handoff-caption{left:24px;bottom:28px;width:min(calc(100vw - 48px),410px);padding:0;font-size:11px}.handoff-caption b{font-size:21px}.nav-progress{left:0;right:0;bottom:0;height:3px}}'
s=once(s,old_mobile,new_mobile,'mobile ellipse styles')
s=once(s,'.nav-progress{left:15px;right:15px;bottom:3px}\n','', 'remove old mobile progress inset')
s=once(s,'.fluid-path .fluid-particle{display:none}\n.hero-clouds,.hero-person,.visual-stage,.mask-journey{transform:none!important}', '.fluid-path .fluid-particle{display:none}\n.mask-orbit-node,.mask-orbit-node span{animation:none!important}\n.hero-clouds,.hero-person,.visual-stage,.mask-journey{transform:none!important}', 'reduced motion orbit')

old_markup='<div class="mask-journey" aria-hidden="true"><img src="https://masck-one.vercel.app/images/masck-one-product-angle.webp" alt="" /></div>\n<section class="handoff-page" aria-label="Object System Proof overview"><div class="handoff-stage"><div class="handoff-index"><b>02</b>Object / system / proof</div><div class="handoff-orbit-copy" aria-hidden="true"><div class="handoff-orbit-node" style="--delay:0s"><span>Object.</span></div><div class="handoff-orbit-node" style="--delay:-6s"><span>System.</span></div><div class="handoff-orbit-node" style="--delay:-12s"><span>Proof.</span></div></div><div class="handoff-halo" aria-hidden="true"><span class="orbit"></span><span class="axis"></span></div><div class="handoff-caption"><b>The same object, followed downward.</b><span>As you scroll, MASCK ONE moves from its exterior form into the architecture, systems and evidence behind the product.</span></div></div></section>'
node_markup='<div class="mask-orbit-node" style="--delay:0s"><span>Architecture.</span></div><div class="mask-orbit-node" style="--delay:-6s"><span>Systems.</span></div><div class="mask-orbit-node" style="--delay:-12s"><span>Proof.</span></div>'
new_markup='<div class="mask-journey" aria-hidden="true"><img src="https://masck-one.vercel.app/images/masck-one-product-angle.webp" alt="" /></div>\n<div class="mask-orbit-overlay orbit-back" aria-hidden="true">'+node_markup+'</div>\n<div class="mask-orbit-overlay orbit-front" aria-hidden="true">'+node_markup+'</div>\n<section class="handoff-page" aria-label="Architecture Systems Proof overview"><div class="handoff-stage"><div class="handoff-index"><b>02</b>Architecture / systems / proof</div><div class="handoff-halo" aria-hidden="true"><span class="orbit"></span><span class="axis"></span></div><div class="handoff-caption"><b>The same object, followed downward.</b><span>As you scroll, MASCK ONE moves from its exterior form into the architecture, systems and proof behind the product.</span></div></div></section>'
s=once(s,old_markup,new_markup,'orbit overlay markup')

# JS: drive both front/back orbit layers together.
s=once(s,"const orbitCopy=document.querySelector('.handoff-orbit-copy');", "const orbitCopies=[...document.querySelectorAll('.mask-orbit-overlay')];", 'orbit refs')
s=once(s,"if(orbitCopy&&name!=='object')orbitCopy.style.opacity='0';", "if(name!=='object')orbitCopies.forEach(el=>el.style.opacity='0');", 'orbit view hide')
s=once(s,'if(orbitCopy)orbitCopy.style.opacity=String(orbitReveal);', 'orbitCopies.forEach(el=>el.style.opacity=String(orbitReveal));', 'orbit reveal')
s=once(s,"}else if(journey){journey.style.opacity='0';if(orbitCopy)orbitCopy.style.opacity='0'}", "}else if(journey){journey.style.opacity='0';orbitCopies.forEach(el=>el.style.opacity='0')}", 'orbit fallback')

INDEX.write_text(s)
print('refined', git_blob_sha(INDEX.read_bytes()))
