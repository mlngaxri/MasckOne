from pathlib import Path
import hashlib

ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/'website/index.html'
EXPECTED='30d1c6a091b4424a2fc64eeaba813e6723d28412'

def blob_sha(data:bytes)->str:
    h=hashlib.sha1(); h.update(f'blob {len(data)}\0'.encode()); h.update(data); return h.hexdigest()

def once(s,old,new,label):
    n=s.count(old)
    if n!=1:
        raise RuntimeError(f'{label}: expected 1 match, got {n}')
    return s.replace(old,new,1)

raw=INDEX.read_bytes(); sha=blob_sha(raw)
if sha!=EXPECTED:
    raise RuntimeError(f'unexpected website baseline {sha}')
s=raw.decode()

old='''/* Feature-stage navbar */
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
new='''/* Persistent navigation + visible earth-tone shader */
.header{overflow:hidden;opacity:1;pointer-events:auto;clip-path:none;transform:translateX(-50%);border:2px solid transparent;background:linear-gradient(rgba(248,250,248,.82),rgba(248,250,248,.76)) padding-box,linear-gradient(112deg,#f6f1e8 0%,#738267 20%,#b97e65 42%,#8fa6a2 64%,#c7b28f 82%,#f6f1e8 100%) border-box;background-size:100% 100%,260% 100%;background-position:0 0,0% 50%;backdrop-filter:blur(18px) saturate(1.08);box-shadow:0 14px 42px rgba(24,33,28,.075),inset 0 1px 0 rgba(255,255,255,.38);animation:navShader 12s ease-in-out infinite alternate}
.header>*{opacity:1}
.nav-progress{left:2px;right:2px;bottom:2px;height:3px;border-radius:0 0 999px 999px;background:rgba(24,33,28,.07)}
.nav-progress-fill{background:#738267;box-shadow:0 0 9px rgba(115,130,103,.38)}

/* Seamless campaign ribbons, deliberately slow */
.band-track{display:flex;flex:none;width:max-content;min-width:0;gap:0;animation:marquee 38s linear infinite;will-change:transform}
.band.one .band-track{animation-direction:reverse;animation-duration:44s}
.band-track>span{display:block;flex:0 0 auto;white-space:nowrap;margin:0;padding:0}
@keyframes marquee{from{transform:translate3d(0,0,0)}to{transform:translate3d(-50%,0,0)}}

/* Quality polish: legibility, stable interaction and restrained effects */
.hero-copy p{font-size:clamp(11.5px,.9vw,13px);line-height:1.72;opacity:.72}
.page-copy>p{font-size:clamp(12.5px,.9vw,13.5px);line-height:1.74;opacity:.7}
.handoff-caption span{line-height:1.72;opacity:.72}
.nav button{min-height:36px}
@media(hover:none){.nav button:hover{transform:none}}
@media(max-width:900px){.hero-copy p{font-size:11.5px;line-height:1.68}.page-copy>p{font-size:12.5px;line-height:1.7}.header{backdrop-filter:blur(14px) saturate(1.05)}}
'''
s=once(s,old,new,'replace feature navbar and ribbon overrides')

s=once(s,"const navProgressFill=document.querySelector('.nav-progress-fill');\nconst header=document.querySelector('.header');","const navProgressFill=document.querySelector('.nav-progress-fill');",'remove obsolete header js ref')

old_js='''function updateHeaderVisibility(position=scrollY){
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
'''
new_js='''function updateNavProgress(position=scrollY){
const current=document.querySelector('.view.active');
if(!current||!navProgressFill)return;
const max=Math.max(0,current.scrollHeight-innerHeight);
const progress=max>0?clamp(position/max,0,1):0;
navProgressFill.style.transform=`scaleX(${progress})`;
}
'''
s=once(s,old_js,new_js,'make navbar persistent')

INDEX.write_text(s)
print('refined', blob_sha(INDEX.read_bytes()))
