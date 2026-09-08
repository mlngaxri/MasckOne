from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "website" / "index.html"
MANIFEST_PATH = ROOT / "website" / "images" / "masck-inspection-v17c-manifest.json"
MARKER = "/* Product inspection final v17c */"
EXPECTED_INDEX_BLOB = "4ff1d60b4d627caddd2b1c37b2e21182ac61d8ce"
RAW = "https://raw.githubusercontent.com/mlngaxri/MasckOne/main/website/images"


def git_blob_sha(data: bytes) -> str:
    h = hashlib.sha1()
    h.update(f"blob {len(data)}\0".encode())
    h.update(data)
    return h.hexdigest()


def pct(view: dict, hotspot: str, axis: str) -> float:
    return float(view["hotspots"][hotspot][f"{axis}_percent"])


raw = INDEX.read_bytes()
s = raw.decode("utf-8")
if MARKER in s:
    print("product inspection final v17c already applied")
    raise SystemExit(0)
if git_blob_sha(raw) != EXPECTED_INDEX_BLOB:
    raise RuntimeError(f"website baseline moved: {git_blob_sha(raw)}")
if not MANIFEST_PATH.exists():
    raise RuntimeError("registered product-inspection manifest missing")

manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
if manifest.get("schema") != "MASCK_ONE_WEBSITE_PRODUCT_INSPECTION_V17C":
    raise RuntimeError("unexpected product-inspection manifest schema")
views = manifest["views"]
front = views["front_three_quarter"]
profile = views["side_rear"]
rear = views["rear_three_quarter"]

for view in (front, profile, rear):
    asset = ROOT / "website" / "images" / view["asset"]
    if not asset.exists():
        raise RuntimeError(f"missing product inspection asset {asset.name}")

sources = manifest["sources"]
markup = f'''
<section class="product-inspection inspection-final-v17c" aria-label="MASCK ONE product inspection" data-product-orbit17 data-asset-version="v17c" data-coordinate-frame="{manifest['coordinate_frame']}" data-camera-id="{manifest['camera_id']}" data-exterior-source-sha="{sources['exterior_render_checkpoint_sha']}" data-exterior-current-head-sha="{sources['exterior_current_head_observed_sha']}" data-retention-source-sha="{sources['retention_current_head_sha']}" data-hmi-source-sha="{sources['hmi_decision_head_sha']}" data-dry-side-source-sha="{sources['dry_side_package_head_sha']}">
<div class="orbit17-sticky">
<div class="orbit17-copy">
<div class="orbit17-kicker">Product inspection</div>
<h2>Front to back.</h2>
<p class="orbit17-state-copy" data-orbit17-copy aria-live="polite">A continuous Bone shell keeps the front visually calm.</p>
</div>
<div class="orbit17-stage" data-orbit17-stage data-state="0">
<img class="orbit17-view active" data-orbit17-view="0" src="{RAW}/{front['asset']}" alt="MASCK ONE front three-quarter development view" loading="lazy" decoding="async" />
<img class="orbit17-view" data-orbit17-view="1" src="{RAW}/{profile['asset']}" alt="MASCK ONE side-rear development view showing compact retention" loading="lazy" decoding="async" />
<img class="orbit17-view" data-orbit17-view="2" src="{RAW}/{rear['asset']}" alt="MASCK ONE rear three-quarter development view showing retention and service cover" loading="lazy" decoding="async" />
<div class="orbit17-hotspot orbit17-hotspot-retention" data-orbit17-hotspot="1" style="--hx:{pct(profile,'right_occipital_backer','x'):.3f}%;--hy:{pct(profile,'right_occipital_backer','y'):.3f}%"><i></i><span><b>Bilateral yoke</b>Attachment still open</span></div>
<div class="orbit17-hotspot orbit17-hotspot-hmi topology" data-orbit17-hotspot="1" style="--hx:{pct(profile,'hmi_primary_capacity','x'):.3f}%;--hy:{pct(profile,'hmi_primary_capacity','y'):.3f}%"><i></i><span><b>Control region</b>Mapping in development</span></div>
<div class="orbit17-hotspot orbit17-hotspot-service" data-orbit17-hotspot="2" style="--hx:{pct(rear,'rear_service_cover','x'):.3f}%;--hy:{pct(rear,'rear_service_cover','y'):.3f}%"><i></i><span><b>Service cover</b>Exterior candidate</span></div>
<div class="orbit17-hotspot orbit17-hotspot-backer" data-orbit17-hotspot="2" style="--hx:{pct(rear,'right_occipital_backer','x'):.3f}%;--hy:{pct(rear,'right_occipital_backer','y'):.3f}%"><i></i><span><b>Occipital backer</b>Fit not validated</span></div>
</div>
<nav class="orbit17-rail" aria-label="Product inspection views">
<button class="orbit17-step active" type="button" data-orbit17-step="0" aria-pressed="true"><i>01</i><span>Front</span></button>
<button class="orbit17-step" type="button" data-orbit17-step="1" aria-pressed="false"><i>02</i><span>Profile</span></button>
<button class="orbit17-step" type="button" data-orbit17-step="2" aria-pressed="false"><i>03</i><span>Rear</span></button>
</nav>
<div class="orbit17-meta"><span>Registered development geometry</span><span>Fit, attachment and control mapping remain open.</span></div>
<div class="orbit17-progress" data-orbit17-progress aria-hidden="true"></div>
</div>
</section>'''.strip()

if "—" in markup or "–" in markup:
    raise RuntimeError("Prompt 17 website copy contains a prohibited dash")

pattern = re.compile(
    r'<section class="product-inspection"[^>]*>.*?</section>\n</section>\n\n<section class="view" data-view="system"',
    re.S,
)
matches = list(pattern.finditer(s))
if len(matches) != 1:
    raise RuntimeError(f"expected one provisional product-inspection chapter, found {len(matches)}")
s = pattern.sub(markup + '\n</section>\n\n<section class="view" data-view="system"', s, count=1)

css = r'''
/* Product inspection final v17c */
.product-inspection.inspection-final-v17c{height:300svh;background:radial-gradient(circle at 65% 48%,rgba(255,255,255,.9),rgba(255,255,255,0) 28%),linear-gradient(145deg,#f7f7f2 0%,#eef1eb 58%,#e7eef0 100%)}
.orbit17-sticky{position:sticky;top:0;height:100svh;min-height:660px;overflow:hidden;isolation:isolate}
.orbit17-sticky:before{content:"";position:absolute;left:63%;top:50%;width:min(60vw,820px);aspect-ratio:1;transform:translate(-50%,-50%);border-radius:50%;background:radial-gradient(circle,rgba(255,255,255,.72),rgba(255,255,255,.18) 46%,transparent 72%);pointer-events:none}
.orbit17-copy{position:absolute;z-index:9;left:max(var(--pad),5vw);top:50%;width:min(410px,31vw);transform:translateY(-50%)}
.orbit17-kicker{display:flex;align-items:center;gap:11px;margin-bottom:18px;font:400 8px/1 DM Mono,monospace;letter-spacing:.145em;text-transform:uppercase;opacity:.48}
.orbit17-kicker:before{content:"";width:29px;height:1px;background:currentColor;opacity:.48}
.orbit17-copy h2{margin:0;font:400 clamp(64px,6.7vw,104px)/.82 Instrument Serif,serif;letter-spacing:-.055em;max-width:430px}
.orbit17-state-copy{max-width:370px;min-height:4.5em;margin:24px 0 0;padding-top:13px;border-top:1px solid rgba(24,33,28,.16);font:500 clamp(13px,1vw,16px)/1.58 Manrope,system-ui,sans-serif;letter-spacing:-.014em;color:rgba(24,33,28,.65)}
.orbit17-stage{position:absolute;z-index:4;left:64%;top:50%;width:min(62vw,860px);aspect-ratio:1;transform:translate(-50%,-50%);touch-action:pan-y}
.orbit17-view{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;opacity:0;transform:scale(.985);filter:drop-shadow(0 24px 28px rgba(24,33,28,.08)) drop-shadow(0 54px 70px rgba(24,33,28,.08));transition:opacity .6s var(--ease),transform .9s var(--ease);pointer-events:none}
.orbit17-view.active{opacity:1;transform:scale(1)}
.orbit17-hotspot{position:absolute;z-index:8;left:var(--hx);top:var(--hy);width:12px;height:12px;transform:translate(-50%,-50%);opacity:0;pointer-events:none;transition:opacity .35s var(--ease)}
.orbit17-hotspot.visible{opacity:1;pointer-events:auto}
.orbit17-hotspot i{position:absolute;inset:2px;border:1px solid rgba(24,33,28,.52);border-radius:50%;background:rgba(247,247,242,.92)}
.orbit17-hotspot i:after{content:"";position:absolute;left:9px;top:4px;width:34px;height:1px;background:rgba(24,33,28,.34)}
.orbit17-hotspot span{position:absolute;left:49px;top:-9px;width:max-content;max-width:170px;padding:7px 9px;border:1px solid rgba(24,33,28,.11);border-radius:8px;background:rgba(247,247,242,.84);backdrop-filter:blur(12px);font:400 6.5px/1.45 DM Mono,monospace;letter-spacing:.07em;text-transform:uppercase;color:rgba(24,33,28,.55)}
.orbit17-hotspot span b{display:block;margin-bottom:3px;font-weight:400;color:rgba(24,33,28,.84)}
.orbit17-hotspot.topology i{border-style:dashed}.orbit17-hotspot.topology i:after{background:repeating-linear-gradient(90deg,rgba(24,33,28,.32) 0 4px,transparent 4px 7px)}
.orbit17-hotspot-service span,.orbit17-hotspot-backer span{left:auto;right:49px;text-align:right}.orbit17-hotspot-service i:after,.orbit17-hotspot-backer i:after{left:auto;right:9px}
.orbit17-rail{position:absolute;z-index:10;right:max(var(--pad),4.8vw);top:50%;width:154px;transform:translateY(-50%);border-top:1px solid rgba(24,33,28,.15)}
.orbit17-step{appearance:none;width:100%;display:grid;grid-template-columns:30px 1fr;align-items:center;gap:9px;min-height:52px;padding:0;border:0;border-bottom:1px solid rgba(24,33,28,.11);background:transparent;color:rgba(24,33,28,.38);text-align:left;cursor:pointer;transition:color .22s var(--ease),transform .22s var(--ease)}
.orbit17-step i{font:400 6px/1 DM Mono,monospace;font-style:normal;opacity:.55}.orbit17-step span{font:400 8px/1 DM Mono,monospace;letter-spacing:.1em;text-transform:uppercase}.orbit17-step.active{color:rgba(24,33,28,.9)}.orbit17-step.active i{color:var(--clay);opacity:1}.orbit17-step:focus-visible{outline:1px solid currentColor;outline-offset:4px}
@media(hover:hover) and (pointer:fine){.orbit17-step:hover{color:var(--ink);transform:translateX(-3px)}.orbit17-hotspot:hover span{background:rgba(247,247,242,.97)}}
.orbit17-meta{position:absolute;z-index:10;left:max(var(--pad),5vw);right:max(var(--pad),4.8vw);bottom:24px;display:flex;justify-content:space-between;gap:20px;padding-top:9px;border-top:1px solid rgba(24,33,28,.11);font:400 6.5px/1.45 DM Mono,monospace;letter-spacing:.08em;text-transform:uppercase;color:rgba(24,33,28,.4)}
.orbit17-meta span:last-child{text-align:right}.orbit17-progress{position:absolute;z-index:10;left:0;bottom:0;width:100%;height:2px;background:var(--ink);opacity:.34;transform:scaleX(0);transform-origin:left center}
@media(max-width:1080px) and (min-width:901px){.orbit17-stage{left:61%;width:63vw}.orbit17-rail{right:2.5vw;width:132px}.orbit17-copy{width:30vw}}
@media(max-width:900px){.product-inspection.inspection-final-v17c{height:280svh}.orbit17-sticky{min-height:560px}.orbit17-sticky:before{left:50%;top:59%;width:100vw}.orbit17-copy{left:22px;right:22px;top:11.5svh;width:auto;transform:none}.orbit17-kicker{font-size:6.5px;margin-bottom:12px}.orbit17-copy h2{font-size:clamp(50px,14.5vw,68px);line-height:.84}.orbit17-state-copy{max-width:85vw;min-height:3.4em;margin-top:13px;padding-top:9px;font-size:12px;line-height:1.5}.orbit17-stage{left:50%;top:58%;width:104vw;max-width:590px}.orbit17-hotspot span{font-size:5.8px;max-width:128px;padding:5px 7px}.orbit17-hotspot i:after{width:22px}.orbit17-hotspot span{left:37px}.orbit17-hotspot-service span,.orbit17-hotspot-backer span{left:auto;right:37px}.orbit17-rail{left:22px;right:22px;top:auto;bottom:max(58px,calc(44px + env(safe-area-inset-bottom)));width:auto;transform:none;display:grid;grid-template-columns:repeat(3,1fr)}.orbit17-step{grid-template-columns:1fr;gap:4px;min-height:46px;padding:7px 0;border-bottom:0;border-right:1px solid rgba(24,33,28,.11)}.orbit17-step:last-child{border-right:0}.orbit17-step i,.orbit17-step span{text-align:center}.orbit17-meta{left:22px;right:22px;bottom:max(16px,env(safe-area-inset-bottom));font-size:5.5px}.orbit17-meta span:first-child{display:none}}
@media(max-width:390px){.orbit17-copy{left:18px;right:18px}.orbit17-stage{top:59%;width:110vw}.orbit17-rail,.orbit17-meta{left:18px;right:18px}.orbit17-hotspot span{display:none}}
@media(prefers-reduced-motion:reduce){.orbit17-view,.orbit17-hotspot,.orbit17-step{transition:none!important}}
'''

s = s.replace("\n</style>\n</head>", css + "\n</style>\n</head>", 1)

js = r'''
<script>
(()=>{
const section=document.querySelector('[data-product-orbit17]');
if(!section)return;
const stage=section.querySelector('[data-orbit17-stage]');
const copy=section.querySelector('[data-orbit17-copy]');
const progress=section.querySelector('[data-orbit17-progress]');
const views=[...section.querySelectorAll('[data-orbit17-view]')];
const steps=[...section.querySelectorAll('[data-orbit17-step]')];
const hotspots=[...section.querySelectorAll('[data-orbit17-hotspot]')];
const reduce=matchMedia('(prefers-reduced-motion: reduce)');
const hover=matchMedia('(hover:hover) and (pointer:fine)');
const lines=[
  'A continuous Bone shell keeps the front visually calm.',
  'The current profile shows shell depth and bilateral retention. Final fit remains under validation.',
  'The rear stays lateral and compact around a central service cover, without a headset-style housing.'
];
let current=0,raf=0,touchX=null,pointerTimer=0;
function setState(index){
  index=Math.max(0,Math.min(2,index));
  current=index;
  stage.dataset.state=String(index);
  if(copy)copy.textContent=lines[index];
  views.forEach((el,i)=>el.classList.toggle('active',i===index));
  steps.forEach((el,i)=>{const on=i===index;el.classList.toggle('active',on);el.setAttribute('aria-pressed',String(on))});
  hotspots.forEach(el=>el.classList.toggle('visible',Number(el.dataset.orbit17Hotspot)===index));
}
function metrics(){const top=section.getBoundingClientRect().top+scrollY;return{top,travel:Math.max(1,section.offsetHeight-innerHeight)}}
function go(index){const m=metrics();const centers=[.08,.50,.92];window.scrollTo({top:m.top+m.travel*centers[index],behavior:reduce.matches?'auto':'smooth'})}
function update(){raf=0;const r=section.getBoundingClientRect();const travel=Math.max(1,section.offsetHeight-innerHeight);const p=Math.max(0,Math.min(1,-r.top/travel));if(progress)progress.style.transform=`scaleX(${p})`;const index=p<1/3?0:p<2/3?1:2;setState(index)}
function request(){if(!raf)raf=requestAnimationFrame(update)}
steps.forEach((button,index)=>button.addEventListener('click',()=>go(index)));
if(stage){
  stage.addEventListener('pointermove',e=>{if(!hover.matches)return;clearTimeout(pointerTimer);pointerTimer=setTimeout(()=>{const r=stage.getBoundingClientRect();const x=(e.clientX-r.left)/Math.max(1,r.width);setState(x<.34?0:x<.67?1:2)},70)});
  stage.addEventListener('pointerleave',()=>{clearTimeout(pointerTimer);request()});
  stage.addEventListener('touchstart',e=>{touchX=e.changedTouches[0]?.clientX??null},{passive:true});
  stage.addEventListener('touchend',e=>{if(touchX===null)return;const end=e.changedTouches[0]?.clientX??touchX;const dx=end-touchX;touchX=null;if(Math.abs(dx)<42)return;go(Math.max(0,Math.min(2,current+(dx<0?1:-1))))},{passive:true});
}
addEventListener('scroll',request,{passive:true});addEventListener('resize',request,{passive:true});setState(0);request();
})();
</script>
'''
s = s.replace("\n</body>\n</html>", js + "\n</body>\n</html>", 1)
INDEX.write_text(s, encoding="utf-8")
print("product inspection final v17c", git_blob_sha(INDEX.read_bytes()))
