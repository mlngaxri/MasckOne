from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "website/index.html"
EXPECTED = "d36b356774a4721e29887713148331142ff2d06c"
MARKER = "/* Product inspection and wearability v17 */"


def git_blob_sha(data: bytes) -> str:
    h = hashlib.sha1()
    h.update(f"blob {len(data)}\0".encode())
    h.update(data)
    return h.hexdigest()


def once(s: str, old: str, new: str, label: str) -> str:
    count = s.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected 1 match, got {count}")
    return s.replace(old, new, 1)


raw = INDEX.read_bytes()
sha = git_blob_sha(raw)
s = raw.decode("utf-8")

if MARKER in s:
    print("product inspection v17 already applied")
    raise SystemExit(0)

if sha != EXPECTED:
    raise RuntimeError(f"unexpected website baseline {sha}")

css = r'''
/* Product inspection and wearability v17 */
.product-inspection{
  position:relative;
  height:360svh;
  overflow:clip;
  background:
    radial-gradient(circle at 65% 47%,rgba(255,255,255,.76),rgba(255,255,255,0) 31%),
    linear-gradient(145deg,#f7f7f2 0%,#eef1eb 56%,#e4ecee 100%);
  color:var(--ink);
  border-top:1px solid rgba(24,33,28,.10);
  isolation:isolate;
}
.inspection-sticky{
  position:sticky;
  top:0;
  height:100svh;
  min-height:660px;
  overflow:hidden;
}
.inspection-sticky:before{
  content:"";
  position:absolute;
  z-index:0;
  left:55%;
  top:50%;
  width:min(54vw,760px);
  aspect-ratio:1;
  transform:translate(-50%,-50%);
  border-radius:50%;
  border:1px solid rgba(24,33,28,.065);
  box-shadow:0 0 0 11vw rgba(255,255,255,.08);
  pointer-events:none;
}
.inspection-copy{
  position:absolute;
  z-index:8;
  left:max(var(--pad),5.2vw);
  top:50%;
  width:min(400px,31vw);
  transform:translateY(-50%);
}
.inspection-kicker{
  display:flex;
  align-items:center;
  gap:10px;
  margin-bottom:19px;
  font:400 7px/1 "DM Mono",monospace;
  letter-spacing:.15em;
  text-transform:uppercase;
  color:rgba(24,33,28,.47);
}
.inspection-kicker:before{
  content:"";
  width:29px;
  height:1px;
  background:currentColor;
  opacity:.5;
}
.inspection-copy h2{
  margin:0;
  font:400 clamp(58px,6.2vw,96px)/.82 "Instrument Serif",serif;
  letter-spacing:-.048em;
  text-wrap:balance;
}
.inspection-copy>p{
  max-width:365px;
  margin:24px 0 0;
  padding-top:13px;
  border-top:1px solid rgba(24,33,28,.16);
  font-size:12px;
  line-height:1.68;
  color:rgba(24,33,28,.64);
}
.inspection-state-copy{
  min-height:2.8em;
  transition:opacity .22s var(--ease),transform .36s var(--ease);
}
.inspection-stage{
  position:absolute;
  z-index:4;
  left:64%;
  top:50%;
  width:min(49vw,700px);
  aspect-ratio:1;
  transform:translate(-50%,-50%);
}
.inspection-product{
  position:absolute;
  z-index:4;
  left:50%;
  top:50%;
  width:min(64%,430px);
  height:auto;
  transform:translate(-50%,-50%);
  filter:drop-shadow(0 19px 29px rgba(24,33,28,.10)) drop-shadow(0 48px 64px rgba(24,33,28,.07));
  transition:transform .8s var(--ease),filter .6s var(--ease),opacity .45s var(--ease);
}
.inspection-stage[data-state="0"] .inspection-product{transform:translate(-50%,-50%) rotate(-1deg) scale(1.02)}
.inspection-stage[data-state="1"] .inspection-product{transform:translate(-50%,-50%) rotate(-1deg) scale(.96)}
.inspection-stage[data-state="2"] .inspection-product{transform:translate(-50%,-50%) rotate(0deg) scale(.93)}
.inspection-stage[data-state="3"] .inspection-product{transform:translate(-50%,-50%) rotate(0deg) scale(.91)}
.inspection-overlay{
  position:absolute;
  z-index:5;
  inset:0;
  opacity:0;
  transform:translateY(8px);
  transition:opacity .34s var(--ease),transform .52s var(--ease);
  pointer-events:none;
}
.inspection-overlay.active{opacity:1;transform:none}
.inspection-front-mark{
  position:absolute;
  left:50%;
  bottom:4%;
  transform:translateX(-50%);
  font:400 6.5px/1 "DM Mono",monospace;
  letter-spacing:.15em;
  text-transform:uppercase;
  color:rgba(24,33,28,.40);
  white-space:nowrap;
}
.inspection-front-mark:before{
  content:"";
  display:block;
  width:1px;
  height:36px;
  margin:0 auto 10px;
  background:linear-gradient(rgba(24,33,28,0),rgba(24,33,28,.30));
}
.inspection-depth-bracket{
  position:absolute;
  right:5%;
  top:25%;
  bottom:25%;
  width:21%;
  border-right:1px solid rgba(24,33,28,.31);
}
.inspection-depth-bracket:before,
.inspection-depth-bracket:after{
  content:"";
  position:absolute;
  right:0;
  width:42px;
  height:1px;
  background:rgba(24,33,28,.31);
}
.inspection-depth-bracket:before{top:0}
.inspection-depth-bracket:after{bottom:0}
.inspection-depth-label{
  position:absolute;
  right:-4px;
  top:50%;
  width:176px;
  transform:translate(100%,-50%);
  font:400 6.5px/1.5 "DM Mono",monospace;
  letter-spacing:.12em;
  text-transform:uppercase;
  color:rgba(24,33,28,.52);
}
.inspection-depth-label b{
  display:block;
  margin-bottom:6px;
  font-weight:400;
  color:rgba(24,33,28,.82);
}
.inspection-retention-arc{
  position:absolute;
  z-index:1;
  left:50%;
  top:50%;
  width:78%;
  height:52%;
  transform:translate(-50%,-50%) rotate(-5deg);
  border:1px dashed rgba(24,33,28,.30);
  border-left-color:rgba(24,33,28,.10);
  border-radius:50%;
}
.inspection-retention-arc:after{
  content:"";
  position:absolute;
  right:-2px;
  top:50%;
  width:8px;
  height:8px;
  transform:translate(50%,-50%);
  border:1px solid rgba(24,33,28,.42);
  border-radius:50%;
  background:var(--paper);
}
.inspection-retention-label,
.inspection-rear-label,
.inspection-service-label{
  position:absolute;
  padding-left:36px;
  font:400 6.5px/1.5 "DM Mono",monospace;
  letter-spacing:.12em;
  text-transform:uppercase;
  color:rgba(24,33,28,.50);
}
.inspection-retention-label:before,
.inspection-rear-label:before,
.inspection-service-label:before{
  content:"";
  position:absolute;
  left:0;
  top:.58em;
  width:27px;
  height:1px;
  background:currentColor;
}
.inspection-retention-label{left:4%;top:24%}
.inspection-rear-label{right:-1%;top:48%}
.inspection-retention-label b,
.inspection-rear-label b,
.inspection-service-label b{
  display:block;
  margin-bottom:5px;
  font-weight:400;
  color:rgba(24,33,28,.82);
}
.inspection-service-line{
  position:absolute;
  right:12%;
  bottom:23%;
  width:34%;
  height:19%;
  border-right:1px dashed rgba(185,126,101,.66);
  border-bottom:1px dashed rgba(185,126,101,.66);
  border-radius:0 0 20px 0;
}
.inspection-service-node{
  position:absolute;
  right:4%;
  bottom:11%;
  width:118px;
  height:62px;
  border:1px dashed rgba(185,126,101,.70);
  border-radius:18px;
  background:rgba(185,126,101,.035);
}
.inspection-service-node:before{
  content:"TOPOLOGY";
  position:absolute;
  left:50%;
  top:50%;
  transform:translate(-50%,-50%);
  font:400 6px/1 "DM Mono",monospace;
  letter-spacing:.13em;
  color:rgba(185,126,101,.84);
}
.inspection-service-label{right:1%;bottom:2%;color:rgba(145,89,68,.68)}
.inspection-service-label b{color:rgba(123,73,54,.90)}
.inspection-rail{
  position:absolute;
  z-index:9;
  right:max(var(--pad),5.2vw);
  top:50%;
  width:160px;
  transform:translateY(-50%);
  border-top:1px solid rgba(24,33,28,.16);
}
.inspection-step{
  width:100%;
  appearance:none;
  display:grid;
  grid-template-columns:30px 1fr;
  align-items:center;
  gap:10px;
  min-height:47px;
  padding:0;
  border:0;
  border-bottom:1px solid rgba(24,33,28,.11);
  background:transparent;
  color:rgba(24,33,28,.38);
  text-align:left;
  cursor:pointer;
  transition:color .25s var(--ease),transform .22s var(--ease);
}
.inspection-step i{
  font:400 6px/1 "DM Mono",monospace;
  font-style:normal;
  letter-spacing:.08em;
  opacity:.55;
}
.inspection-step span{
  font:400 8px/1 "DM Mono",monospace;
  letter-spacing:.10em;
  text-transform:uppercase;
}
.inspection-step.active{color:rgba(24,33,28,.88)}
.inspection-step.active i{color:var(--clay);opacity:1}
.inspection-step:focus-visible{outline:2px solid #75866c;outline-offset:4px}
@media(hover:hover) and (pointer:fine){
  .inspection-step:hover{color:var(--ink);transform:translateX(-3px)}
  .inspection-step:active{transform:translateX(-3px) translateY(1px)}
}
.inspection-meta{
  position:absolute;
  z-index:9;
  left:max(var(--pad),5.2vw);
  right:max(var(--pad),5.2vw);
  bottom:24px;
  display:flex;
  justify-content:space-between;
  gap:24px;
  padding-top:10px;
  border-top:1px solid rgba(24,33,28,.12);
  font:400 6.5px/1.45 "DM Mono",monospace;
  letter-spacing:.10em;
  text-transform:uppercase;
  color:rgba(24,33,28,.39);
}
.inspection-meta span:last-child{text-align:right}
.inspection-progress{
  position:absolute;
  z-index:7;
  left:0;
  bottom:0;
  width:100%;
  height:2px;
  transform:scaleX(0);
  transform-origin:left center;
  background:linear-gradient(90deg,var(--clay),#9ba88f 58%,#91afb5);
}
@media(max-width:1100px) and (min-width:901px){
  .inspection-copy{width:min(350px,31vw)}
  .inspection-stage{left:62%;width:min(52vw,620px)}
  .inspection-rail{right:3vw;width:138px}
  .inspection-depth-label{right:0;width:145px}
}
@media(max-width:900px){
  .product-inspection{height:330svh}
  .inspection-sticky{min-height:560px}
  .inspection-sticky:before{left:50%;top:58%;width:92vw;box-shadow:0 0 0 18vw rgba(255,255,255,.07)}
  .inspection-copy{
    left:22px;
    right:22px;
    top:11.8svh;
    width:auto;
    transform:none;
  }
  .inspection-kicker{margin-bottom:13px;font-size:6.25px}
  .inspection-copy h2{font-size:clamp(48px,14vw,64px);line-height:.82}
  .inspection-copy>p{max-width:78vw;margin-top:14px;padding-top:9px;font-size:11.25px;line-height:1.55}
  .inspection-stage{
    left:50%;
    top:58%;
    width:94vw;
    max-width:520px;
  }
  .inspection-product{width:min(58%,330px)}
  .inspection-depth-bracket{right:9%;top:28%;bottom:28%;width:17%}
  .inspection-depth-label{display:none}
  .inspection-retention-label{left:2%;top:21%}
  .inspection-rear-label{right:2%;top:46%;padding-left:28px}
  .inspection-service-node{right:6%;bottom:17%;width:88px;height:48px;border-radius:14px}
  .inspection-service-label{display:none}
  .inspection-rail{
    left:22px;
    right:22px;
    top:auto;
    bottom:max(58px,calc(45px + env(safe-area-inset-bottom)));
    width:auto;
    transform:none;
    display:grid;
    grid-template-columns:repeat(4,1fr);
  }
  .inspection-step{
    grid-template-columns:1fr;
    gap:4px;
    min-height:45px;
    padding:8px 0 6px;
    border-bottom:0;
    border-right:1px solid rgba(24,33,28,.10);
  }
  .inspection-step:last-child{border-right:0}
  .inspection-step i,.inspection-step span{text-align:center}
  .inspection-step span{font-size:6.5px;letter-spacing:.07em}
  .inspection-meta{
    left:22px;
    right:22px;
    bottom:max(16px,env(safe-area-inset-bottom));
    gap:12px;
    padding-top:8px;
    font-size:5.7px;
  }
}
@media(max-width:390px){
  .inspection-copy{left:18px;right:18px}
  .inspection-copy h2{font-size:clamp(44px,14.6vw,58px)}
  .inspection-copy>p{max-width:84vw}
  .inspection-stage{top:59%;width:100vw}
  .inspection-product{width:60%}
  .inspection-retention-label,.inspection-rear-label{font-size:5.7px}
  .inspection-rail{left:18px;right:18px}
  .inspection-step span{font-size:5.8px}
  .inspection-meta{left:18px;right:18px}
}
@media(prefers-reduced-motion:reduce){
  .inspection-product,.inspection-overlay,.inspection-state-copy,.inspection-step{transition:none!important}
}
'''

markup = r'''
<section class="product-inspection" aria-label="MASCK ONE product inspection" data-source-main-sha="5c41702f23ffe5a602b8af363e8588867d9af2e0" data-authority-revision="2026-08-30-R1" data-source-asset-sha="ca2b69b1d37e73f6e907e9cf46d93e44966142c3">
<div class="inspection-sticky">
<div class="inspection-copy">
<div class="inspection-kicker">Product inspection</div>
<h2>Front to back.</h2>
<p class="inspection-state-copy" data-inspection-copy>One continuous Bone exterior defines the front character.</p>
</div>
<div class="inspection-stage" data-inspection-stage data-state="0">
<img class="inspection-product" data-asset-slot="inspection-product" src="https://raw.githubusercontent.com/mlngaxri/MasckOne/main/website/images/masck-hero-mask-v2.webp" alt="MASCK ONE front product view" loading="lazy" decoding="async" />
<div class="inspection-overlay active" data-inspection-overlay="0" aria-hidden="true">
<div class="inspection-front-mark">Front character</div>
</div>
<div class="inspection-overlay" data-inspection-overlay="1" aria-hidden="true">
<div class="inspection-depth-bracket"><div class="inspection-depth-label"><b>Profile depth</b>Not yet frozen</div></div>
</div>
<div class="inspection-overlay" data-inspection-overlay="2" aria-hidden="true">
<div class="inspection-retention-arc"></div>
<div class="inspection-retention-label"><b>Retention</b>Development topology</div>
<div class="inspection-rear-label"><b>Rear package</b>Development location</div>
</div>
<div class="inspection-overlay" data-inspection-overlay="3" aria-hidden="true">
<div class="inspection-service-line"></div>
<div class="inspection-service-node"></div>
<div class="inspection-service-label"><b>Removable cartridge</b>Architecture only</div>
</div>
</div>
<nav class="inspection-rail" aria-label="Product inspection states">
<button class="inspection-step active" type="button" data-inspection-step="0" aria-pressed="true"><i>01</i><span>Front</span></button>
<button class="inspection-step" type="button" data-inspection-step="1" aria-pressed="false"><i>02</i><span>Depth</span></button>
<button class="inspection-step" type="button" data-inspection-step="2" aria-pressed="false"><i>03</i><span>Retention</span></button>
<button class="inspection-step" type="button" data-inspection-step="3" aria-pressed="false"><i>04</i><span>Service</span></button>
</nav>
<div class="inspection-meta">
<span>Control mapping remains under convergence.</span>
<span>Fit and comfort require physical validation.</span>
</div>
<div class="inspection-progress" data-inspection-progress aria-hidden="true"></div>
</div>
</section>'''

js = r'''
<script>
(()=>{
const section=document.querySelector('.product-inspection');
if(!section)return;
const stage=section.querySelector('[data-inspection-stage]');
const copy=section.querySelector('[data-inspection-copy]');
const progress=section.querySelector('[data-inspection-progress]');
const steps=[...section.querySelectorAll('[data-inspection-step]')];
const overlays=[...section.querySelectorAll('[data-inspection-overlay]')];
const reduced=matchMedia('(prefers-reduced-motion: reduce)');
const lines=[
  'One continuous Bone exterior defines the front character.',
  'Final profile depth remains under engineering convergence.',
  'Retention continues behind the head. Final rear geometry remains in development.',
  'A removable cartridge architecture provides the service endpoint.'
];
let current=-1;
let queued=false;

function setState(index){
  index=Math.max(0,Math.min(steps.length-1,index));
  if(index===current)return;
  current=index;
  if(stage)stage.dataset.state=String(index);
  if(copy)copy.textContent=lines[index];
  steps.forEach((button,i)=>{
    const active=i===index;
    button.classList.toggle('active',active);
    button.setAttribute('aria-pressed',String(active));
  });
  overlays.forEach((overlay,i)=>overlay.classList.toggle('active',i===index));
}

function update(){
  queued=false;
  const rect=section.getBoundingClientRect();
  const travel=Math.max(1,section.offsetHeight-innerHeight);
  const p=Math.max(0,Math.min(1,-rect.top/travel));
  if(progress)progress.style.transform=`scaleX(${p})`;
  const index=Math.min(steps.length-1,Math.floor(p*steps.length));
  setState(index);
}

function requestUpdate(){
  if(queued)return;
  queued=true;
  requestAnimationFrame(update);
}

steps.forEach((button,index)=>button.addEventListener('click',()=>{
  const top=section.getBoundingClientRect().top+scrollY;
  const travel=Math.max(1,section.offsetHeight-innerHeight);
  const target=top+travel*((index+.08)/steps.length);
  window.scrollTo({top:target,behavior:reduced.matches?'auto':'smooth'});
}));

addEventListener('scroll',requestUpdate,{passive:true});
addEventListener('resize',requestUpdate,{passive:true});
update();
})();
</script>
'''

s = once(s, "\n</style>\n</head>", css + "\n</style>\n</head>", "insert inspection css")

handoff_anchor = '<section class="handoff-page" aria-label="Architecture Systems Proof overview"><div class="handoff-stage"></div></section>\n</section>\n\n<section class="view" data-view="system"'
handoff_replacement = '<section class="handoff-page" aria-label="Architecture Systems Proof overview"><div class="handoff-stage"></div></section>\n' + markup + '\n</section>\n\n<section class="view" data-view="system"'
s = once(s, handoff_anchor, handoff_replacement, "insert product inspection")

s = once(
    s,
    "journey.style.opacity='1';",
    "journey.style.opacity=String(1-smooth(clamp((sy-(handoffEnd-innerHeight*.08))/(innerHeight*.26),0,1)));",
    "fade hero product before inspection",
)

s = once(s, "\n</body>\n</html>", js + "\n</body>\n</html>", "insert inspection script")

INDEX.write_text(s, encoding="utf-8")
print("product inspection v17", git_blob_sha(INDEX.read_bytes()))
