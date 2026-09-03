from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'website/index.html'
s = INDEX.read_text()

SYSTEM_START = '<section class="view" data-view="system" aria-label="Systems section">'
PROOF_START = '<section class="view" data-view="proof" aria-label="Proof section">'

new_system = r'''<section class="view" data-view="system" aria-label="Systems section">
<section class="systems-experience" aria-label="MASCK ONE live systems architecture">
<div class="systems-sticky">
<div class="systems-atmosphere systems-atmosphere-flow" aria-hidden="true"></div>
<div class="systems-atmosphere systems-atmosphere-motion" aria-hidden="true"></div>
<div class="systems-grid" aria-hidden="true"></div>

<div class="systems-word systems-word-flow" aria-hidden="true">FLOW</div>
<div class="systems-word systems-word-motion" aria-hidden="true">MOTION</div>

<div class="systems-step systems-step-flow" aria-hidden="true"><span>02 / Systems</span><b>01</b></div>
<div class="systems-step systems-step-motion" aria-hidden="true"><span>02 / Systems</span><b>02</b></div>

<div class="systems-copy systems-copy-flow">
<div class="systems-kicker">Contained fluid circuit</div>
<h2>Fresh moves in.<br>Used fluid moves out.</h2>
<p>Supply and return are treated as separate paths through the wearable. Water and cleanser move toward the face while recovered liquid is routed away toward containment.</p>
<div class="systems-facts"><span><b>Supply</b>Metered fresh-water and cleanser distribution.</span><span><b>Return</b>Dedicated recovered-fluid path.</span></div>
</div>

<div class="systems-copy systems-copy-motion">
<div class="systems-kicker">Local motion architecture</div>
<h2>Movement,<br>only where needed.</h2>
<p>Four localized actuation zones divide motion across the facial interface instead of forcing the entire wearable to behave as one rigid moving structure.</p>
<div class="systems-facts"><span><b>Four zones</b>Localized facial actuation architecture.</span><span><b>Control</b>Amplitude and timing remain engineering variables.</span></div>
</div>

<div class="systems-core" data-systems-core aria-hidden="true">
<div class="systems-core-orbit orbit-a"></div>
<div class="systems-core-orbit orbit-b"></div>
<div class="systems-core-axis axis-x"></div>
<div class="systems-core-axis axis-y"></div>

<div class="systems-flow-visual">
<svg class="systems-circuit" viewBox="0 0 620 620" focusable="false">
<path class="circuit-supply" d="M44 420 C122 420 133 162 289 172 C392 178 391 318 485 314 C539 311 552 252 590 224"/>
<path class="circuit-return" d="M46 465 C139 465 170 520 286 496 C404 471 392 372 492 382 C545 387 554 425 594 444"/>
<circle class="circuit-dot supply-dot" r="5"><animateMotion dur="5.8s" repeatCount="indefinite" path="M44 420 C122 420 133 162 289 172 C392 178 391 318 485 314 C539 311 552 252 590 224"/></circle>
<circle class="circuit-dot return-dot" r="5"><animateMotion dur="6.7s" repeatCount="indefinite" path="M594 444 C554 425 545 387 492 382 C392 372 404 471 286 496 C170 520 139 465 46 465"/></circle>
</svg>
<div class="systems-port port-supply"><i></i><span>SUPPLY</span><b>IN</b></div>
<div class="systems-port port-return"><i></i><span>RETURN</span><b>OUT</b></div>
<div class="systems-product-frame">
<img src="https://masck-one.vercel.app/images/chapter-manifold-v2.webp" alt="" loading="lazy" decoding="async" />
</div>
</div>

<div class="systems-motion-visual">
<div class="actuation-wave wave-1"></div><div class="actuation-wave wave-2"></div><div class="actuation-wave wave-3"></div>
<div class="systems-product-frame">
<img src="https://masck-one.vercel.app/images/chapter-chassis-v2.webp" alt="" loading="lazy" decoding="async" />
</div>
<div class="actuation-zone zone-a"><i></i><span>A</span></div>
<div class="actuation-zone zone-b"><i></i><span>B</span></div>
<div class="actuation-zone zone-c"><i></i><span>C</span></div>
<div class="actuation-zone zone-d"><i></i><span>D</span></div>
</div>
</div>

<div class="systems-readout systems-readout-flow readout-left"><b>FLOW / 01</b><span>Fresh-water + cleanser supply</span></div>
<div class="systems-readout systems-readout-flow readout-right"><b>FLOW / 02</b><span>Recovered-fluid return</span></div>
<div class="systems-readout systems-readout-motion readout-left"><b>MOTION / A-D</b><span>Four localized zones</span></div>
<div class="systems-readout systems-readout-motion readout-right"><b>CONTROL</b><span>Amplitude + timing remain variable</span></div>

<div class="systems-timeline" aria-hidden="true"><span>FLOW</span><div class="systems-timeline-track"><i class="systems-timeline-fill"></i><b class="systems-timeline-dot"></b></div><span>MOTION</span></div>
<div class="systems-evidence systems-evidence-flow">Flow rate, recovery efficiency and leakage remain physical evidence gates.</div>
<div class="systems-evidence systems-evidence-motion">Motion amplitude, force, acoustic perception and comfort remain unvalidated.</div>
</div>
</section>
</section>

'''

if SYSTEM_START not in s or PROOF_START not in s:
    raise RuntimeError('systems/proof boundaries not found')
start = s.index(SYSTEM_START)
end = s.index(PROOF_START, start)
s = s[:start] + new_system + s[end:]

css_marker = '/* Systems live circuit v9 */'
css = r'''
/* Systems live circuit v9 */
.systems-experience{position:relative;height:230svh;background:#17201b;color:#f5f6ef;border-top:1px solid rgba(255,255,255,.08);isolation:isolate}
.systems-sticky{position:sticky;top:0;height:100svh;overflow:hidden;isolation:isolate;background:#17201b}
.systems-atmosphere,.systems-grid,.systems-word,.systems-core,.systems-copy,.systems-step,.systems-readout,.systems-timeline,.systems-evidence{position:absolute}
.systems-atmosphere{inset:-10%;z-index:0;pointer-events:none}
.systems-atmosphere-flow{background:radial-gradient(circle at 61% 47%,rgba(140,180,186,.18),transparent 26%),radial-gradient(circle at 75% 73%,rgba(185,126,101,.13),transparent 24%),linear-gradient(145deg,#17201b 4%,#1d2923 55%,#26342b 100%)}
.systems-atmosphere-motion{background:radial-gradient(circle at 63% 48%,rgba(225,235,214,.20),transparent 27%),radial-gradient(circle at 76% 28%,rgba(185,126,101,.12),transparent 21%),linear-gradient(145deg,#1e2821 0%,#64705b 62%,#a9b59a 145%);opacity:0}
.systems-grid{z-index:1;inset:7% 5%;opacity:.085;background-image:linear-gradient(to right,currentColor 1px,transparent 1px),linear-gradient(to bottom,currentColor 1px,transparent 1px);background-size:8.333% 10%;-webkit-mask-image:radial-gradient(circle at 61% 49%,#000 0 46%,transparent 80%);mask-image:radial-gradient(circle at 61% 49%,#000 0 46%,transparent 80%)}
.systems-grid:after{content:"";position:absolute;inset:0;background:linear-gradient(90deg,transparent 49.94%,rgba(255,255,255,.4) 50%,transparent 50.06%),linear-gradient(transparent 49.94%,rgba(255,255,255,.3) 50%,transparent 50.06%);opacity:.22}
.systems-word{z-index:1;font:300 clamp(150px,22vw,350px)/.72 Fraunces,serif;letter-spacing:-.085em;white-space:nowrap;pointer-events:none;opacity:.07;will-change:opacity,transform}
.systems-word-flow{right:-2vw;bottom:4vh}
.systems-word-motion{left:-2vw;bottom:3vh;opacity:0}
.systems-step{z-index:9;top:92px;right:var(--pad);min-width:170px;padding-top:9px;border-top:1px solid rgba(255,255,255,.24);display:flex;align-items:baseline;justify-content:space-between;gap:26px;font:400 8px/1 DM Mono,monospace;letter-spacing:.13em;text-transform:uppercase;color:rgba(255,255,255,.58);will-change:opacity,transform}
.systems-step b{font:300 32px/.8 Fraunces,serif;letter-spacing:-.05em;color:#f5f6ef}
.systems-step-motion{opacity:0}
.systems-copy{z-index:8;left:var(--pad);top:50%;width:min(470px,34vw);transform:translateY(-50%);will-change:opacity,transform}
.systems-copy-motion{left:auto;right:var(--pad);width:min(450px,32vw);opacity:0}
.systems-kicker{display:flex;align-items:center;gap:11px;margin-bottom:19px;font:400 8px/1 DM Mono,monospace;letter-spacing:.145em;text-transform:uppercase;color:rgba(245,246,239,.56)}
.systems-kicker:before{content:"";width:30px;height:1px;background:currentColor}
.systems-copy h2{margin:0;font:300 clamp(49px,5.5vw,84px)/.87 Fraunces,serif;letter-spacing:-.06em;text-wrap:balance}
.systems-copy p{max-width:390px;margin:24px 0 0;padding-top:14px;border-top:1px solid rgba(255,255,255,.19);font-size:12.5px;line-height:1.74;color:rgba(245,246,239,.67)}
.systems-facts{display:grid;grid-template-columns:1fr 1fr;margin-top:32px;border-top:1px solid rgba(255,255,255,.18);font-size:10px;line-height:1.55;color:rgba(245,246,239,.58)}
.systems-facts span{min-height:86px;padding:15px 18px 10px 0}
.systems-facts span+span{padding-left:18px;border-left:1px solid rgba(255,255,255,.15)}
.systems-facts b{display:block;margin-bottom:12px;font:500 7.5px/1 DM Mono,monospace;letter-spacing:.13em;text-transform:uppercase;color:rgba(245,246,239,.92)}
.systems-core{z-index:5;left:61.5%;top:50%;width:clamp(390px,39vw,620px);aspect-ratio:1;transform:translate(-50%,-50%);will-change:transform}
.systems-core:before{content:"";position:absolute;inset:12%;border-radius:50%;background:radial-gradient(circle,rgba(255,255,255,.12),rgba(255,255,255,.035) 39%,transparent 69%);filter:blur(9px)}
.systems-core-orbit{position:absolute;left:50%;top:50%;border:1px solid rgba(245,246,239,.17);border-radius:50%;transform:translate(-50%,-50%) rotate(-11deg) scaleY(.52);pointer-events:none}
.systems-core-orbit.orbit-a{width:102%;height:102%;animation:systemOrbit 21s linear infinite}
.systems-core-orbit.orbit-b{width:78%;height:78%;border-style:dashed;border-color:rgba(185,126,101,.25);animation:systemOrbitReverse 27s linear infinite}
@keyframes systemOrbit{to{transform:translate(-50%,-50%) rotate(349deg) scaleY(.52)}}
@keyframes systemOrbitReverse{to{transform:translate(-50%,-50%) rotate(-371deg) scaleY(.52)}}
.systems-core-axis{position:absolute;z-index:0;left:50%;top:50%;background:rgba(245,246,239,.13);pointer-events:none}
.systems-core-axis.axis-x{width:112%;height:1px;transform:translate(-50%,-50%)}
.systems-core-axis.axis-y{width:1px;height:112%;transform:translate(-50%,-50%)}
.systems-flow-visual,.systems-motion-visual{position:absolute;z-index:3;inset:0;display:grid;place-items:center;will-change:opacity,transform}
.systems-motion-visual{opacity:0}
.systems-product-frame{position:absolute;z-index:4;inset:13%;display:grid;place-items:center}
.systems-product-frame:before{content:"";position:absolute;inset:10%;border:1px solid rgba(245,246,239,.08);border-radius:48%;transform:rotate(4deg)}
.systems-product-frame img{position:relative;z-index:2;width:100%;height:100%;object-fit:contain;filter:drop-shadow(0 20px 28px rgba(0,0,0,.2)) drop-shadow(0 44px 58px rgba(0,0,0,.18))}
.systems-circuit{position:absolute;z-index:2;inset:-2%;width:104%;height:104%;overflow:visible}
.systems-circuit path{fill:none;stroke-width:1.3;stroke-linecap:round;stroke-dasharray:5 9}
.circuit-supply{stroke:#a9cbd0;animation:systemDash 8s linear infinite}
.circuit-return{stroke:#cb987f;animation:systemDashBack 10s linear infinite}
@keyframes systemDash{to{stroke-dashoffset:-112}}
@keyframes systemDashBack{to{stroke-dashoffset:112}}
.circuit-dot{filter:drop-shadow(0 0 5px currentColor)}
.supply-dot{fill:#c5e4e7;color:#c5e4e7}.return-dot{fill:#d3a08a;color:#d3a08a}
.systems-port{position:absolute;z-index:7;display:grid;grid-template-columns:auto auto;grid-template-rows:auto auto;column-gap:8px;align-items:center;font:400 7.5px/1 DM Mono,monospace;letter-spacing:.13em;text-transform:uppercase;color:rgba(245,246,239,.62)}
.systems-port i{grid-row:1/3;width:8px;height:8px;border-radius:50%;background:currentColor;box-shadow:0 0 0 5px rgba(255,255,255,.05)}
.systems-port b{font-size:7px;font-weight:400;color:rgba(245,246,239,.36)}
.port-supply{left:2%;bottom:19%;color:#b8dadd}.port-return{right:-1%;bottom:12%;color:#d4a18a;text-align:right}
.actuation-wave{position:absolute;left:50%;top:50%;width:56%;aspect-ratio:1;border:1px solid rgba(232,239,224,.22);border-radius:50%;transform:translate(-50%,-50%);animation:actuationWave 2.45s ease-out infinite}
.wave-2{animation-delay:.7s}.wave-3{animation-delay:1.4s}
@keyframes actuationWave{0%{transform:translate(-50%,-50%) scale(.72);opacity:0}24%{opacity:.55}100%{transform:translate(-50%,-50%) scale(1.4);opacity:0}}
.actuation-zone{position:absolute;z-index:8;width:42px;height:42px;display:grid;place-items:center;border:1px solid rgba(245,246,239,.34);border-radius:50%;font:400 9px/1 DM Mono,monospace;color:#f5f6ef;background:rgba(23,32,27,.42);backdrop-filter:blur(8px);animation:actuationNode 3.2s ease-in-out infinite}
.actuation-zone i{position:absolute;inset:5px;border:1px solid rgba(185,126,101,.32);border-radius:50%}
.zone-a{left:26%;top:23%}.zone-b{right:25%;top:28%;animation-delay:.55s}.zone-c{left:29%;bottom:24%;animation-delay:1.1s}.zone-d{right:24%;bottom:25%;animation-delay:1.65s}
@keyframes actuationNode{0%,58%,100%{transform:scale(.94);box-shadow:0 0 0 0 rgba(215,226,203,0)}72%{transform:scale(1.08);box-shadow:0 0 0 12px rgba(215,226,203,.07)}}
.systems-readout{z-index:7;width:190px;padding-top:9px;border-top:1px solid rgba(245,246,239,.18);font:400 7.5px/1.55 DM Mono,monospace;letter-spacing:.08em;text-transform:uppercase;color:rgba(245,246,239,.44);will-change:opacity,transform}
.systems-readout b{display:block;margin-bottom:6px;font-weight:400;letter-spacing:.14em;color:rgba(245,246,239,.72)}
.readout-left{left:46%;top:19%}.readout-right{right:4%;bottom:18%;text-align:right}
.systems-readout-motion{opacity:0}
.systems-timeline{z-index:10;left:50%;bottom:25px;transform:translateX(-50%);display:flex;align-items:center;gap:12px;font:400 7px/1 DM Mono,monospace;letter-spacing:.13em;text-transform:uppercase;color:rgba(245,246,239,.42)}
.systems-timeline-track{position:relative;width:120px;height:1px;background:rgba(245,246,239,.16)}
.systems-timeline-fill{position:absolute;left:0;top:0;width:100%;height:1px;background:#c5d5ba;transform:scaleX(0);transform-origin:left}
.systems-timeline-dot{position:absolute;left:0;top:50%;width:7px;height:7px;border:1px solid #c5d5ba;border-radius:50%;background:#17201b;transform:translate(-50%,-50%)}
.systems-evidence{z-index:8;left:var(--pad);bottom:22px;max-width:450px;font:400 7.5px/1.45 DM Mono,monospace;letter-spacing:.055em;text-transform:uppercase;color:rgba(245,246,239,.34);will-change:opacity}
.systems-evidence-motion{opacity:0}
@media(min-width:901px) and (max-width:1180px){.systems-copy{width:min(390px,36vw)}.systems-copy-motion{width:min(380px,34vw)}.systems-core{left:62%;width:clamp(390px,43vw,520px)}.systems-readout{display:none}}
@media(max-width:900px){
  .systems-experience{height:210svh}
  .systems-sticky{min-height:680px}
  .systems-grid{inset:5% 12px;background-size:16.666% 10%;opacity:.065}
  .systems-step{top:max(78px,calc(env(safe-area-inset-top) + 64px));right:20px;min-width:122px}
  .systems-step b{font-size:25px}
  .systems-copy,.systems-copy-motion{left:22px;right:22px;top:13svh;width:auto;transform:none}
  .systems-copy h2{max-width:76vw;font-size:clamp(42px,11.8vw,61px);line-height:.88}
  .systems-copy p{max-width:75vw;margin-top:16px;padding-top:10px;font-size:12px;line-height:1.62}
  .systems-facts{display:none}
  .systems-core{left:50%;top:61%;width:min(88vw,430px)}
  .systems-word{font-size:clamp(118px,34vw,180px);bottom:8vh}
  .systems-word-flow{right:-9vw}.systems-word-motion{left:-10vw}
  .systems-readout{display:none}
  .systems-evidence{left:22px;right:22px;bottom:max(48px,calc(34px + env(safe-area-inset-bottom)));max-width:none;font-size:7px}
  .systems-timeline{bottom:max(18px,env(safe-area-inset-bottom))}
  .actuation-zone{width:34px;height:34px}
  .systems-port{font-size:6.5px}
}
@media(max-width:390px){.systems-copy,.systems-copy-motion{left:18px;right:18px}.systems-copy h2{max-width:82vw;font-size:clamp(40px,12.5vw,52px)}.systems-copy p{max-width:82vw}.systems-core{top:62%;width:92vw}.systems-step{right:18px}}
@media(max-width:900px) and (prefers-reduced-motion:reduce){.systems-core-orbit,.systems-circuit path,.actuation-wave,.actuation-zone{animation:none!important}.systems-circuit .circuit-dot{display:none}}
'''

# Replace prior v9 block if rerun, otherwise append before </style>.
if css_marker in s:
    cstart = s.index(css_marker)
    cend = s.index('</style>', cstart)
    s = s[:cstart] + css + '\n' + s[cend:]
else:
    s = s.replace('\n</style>\n</head>', '\n' + css + '\n</style>\n</head>', 1)

# Install state references once.
decl_anchor = "const bandTracks=[...document.querySelectorAll('.hero .band-track')];"
declarations = decl_anchor + r'''
const systemExperience=document.querySelector('.systems-experience');
const systemSticky=document.querySelector('.systems-sticky');
const systemsAtmosphereMotion=document.querySelector('.systems-atmosphere-motion');
const systemsFlowVisual=document.querySelector('.systems-flow-visual');
const systemsMotionVisual=document.querySelector('.systems-motion-visual');
const systemsCopyFlow=document.querySelector('.systems-copy-flow');
const systemsCopyMotion=document.querySelector('.systems-copy-motion');
const systemsWordFlow=document.querySelector('.systems-word-flow');
const systemsWordMotion=document.querySelector('.systems-word-motion');
const systemsStepFlow=document.querySelector('.systems-step-flow');
const systemsStepMotion=document.querySelector('.systems-step-motion');
const systemsCore=document.querySelector('[data-systems-core]');
const systemsTimelineFill=document.querySelector('.systems-timeline-fill');
const systemsTimelineDot=document.querySelector('.systems-timeline-dot');
const systemsReadoutFlow=[...document.querySelectorAll('.systems-readout-flow')];
const systemsReadoutMotion=[...document.querySelectorAll('.systems-readout-motion')];
const systemsEvidenceFlow=document.querySelector('.systems-evidence-flow');
const systemsEvidenceMotion=document.querySelector('.systems-evidence-motion');'''
if 'const systemExperience=' not in s:
    if decl_anchor not in s:
        raise RuntimeError('JS declaration anchor missing')
    s = s.replace(decl_anchor, declarations, 1)

render_anchor = "if(active==='object'&&hero){"
systems_render = r'''if(active==='system'&&systemExperience&&systemSticky){
const range=Math.max(1,systemExperience.offsetHeight-innerHeight);
const sp=clamp(sy/range,0,1);
const phase=lowMotion()?(sp>=.5?1:0):smooth(clamp((sp-.42)/.18,0,1));
const flowOut=smooth(clamp((sp-.26)/.18,0,1));
const motionIn=smooth(clamp((sp-.50)/.18,0,1));
const coreLift=mix(0,-18,phase);
if(systemsAtmosphereMotion)systemsAtmosphereMotion.style.opacity=String(phase);
if(systemsFlowVisual){systemsFlowVisual.style.opacity=String(1-phase);systemsFlowVisual.style.transform=`scale(${1-phase*.045}) rotate(${phase*-2}deg)`}
if(systemsMotionVisual){systemsMotionVisual.style.opacity=String(phase);systemsMotionVisual.style.transform=`scale(${.96+phase*.04}) rotate(${mix(2,0,phase)}deg)`}
if(systemsCopyFlow){systemsCopyFlow.style.opacity=String(1-flowOut);systemsCopyFlow.style.transform=desktop()?`translateY(calc(-50% + ${flowOut*-22}px))`:`translateY(${flowOut*-16}px)`}
if(systemsCopyMotion){systemsCopyMotion.style.opacity=String(motionIn);systemsCopyMotion.style.transform=desktop()?`translateY(calc(-50% + ${(1-motionIn)*22}px))`:`translateY(${(1-motionIn)*18}px)`}
if(systemsWordFlow){systemsWordFlow.style.opacity=String(.075*(1-phase));systemsWordFlow.style.transform=`translate3d(${sp*-42}px,${sp*12}px,0)`}
if(systemsWordMotion){systemsWordMotion.style.opacity=String(.07*phase);systemsWordMotion.style.transform=`translate3d(${(1-sp)*38}px,${(1-sp)*12}px,0)`}
if(systemsStepFlow){systemsStepFlow.style.opacity=String(1-phase);systemsStepFlow.style.transform=`translateY(${phase*-10}px)`}
if(systemsStepMotion){systemsStepMotion.style.opacity=String(phase);systemsStepMotion.style.transform=`translateY(${(1-phase)*10}px)`}
if(systemsCore)systemsCore.style.transform=`translate(-50%,-50%) translate3d(${desktop()?mx*7:0}px,${coreLift+(desktop()?my*5:0)}px,0) rotate(${mix(-1.5,1.5,phase)}deg) scale(${1+Math.sin(sp*Math.PI)*.018})`;
systemsReadoutFlow.forEach((el,i)=>{el.style.opacity=String((1-phase)*(.62+i*.05));el.style.transform=`translateY(${phase*(i?14:-14)}px)`});
systemsReadoutMotion.forEach((el,i)=>{el.style.opacity=String(phase*(.62+i*.05));el.style.transform=`translateY(${(1-phase)*(i?-14:14)}px)`});
if(systemsEvidenceFlow)systemsEvidenceFlow.style.opacity=String((1-phase)*.9);
if(systemsEvidenceMotion)systemsEvidenceMotion.style.opacity=String(phase*.9);
if(systemsTimelineFill)systemsTimelineFill.style.transform=`scaleX(${sp})`;
if(systemsTimelineDot)systemsTimelineDot.style.left=`${sp*100}%`;
}

''' + render_anchor
if 'const range=Math.max(1,systemExperience.offsetHeight-innerHeight);' not in s:
    if render_anchor not in s:
        raise RuntimeError('render anchor missing')
    s = s.replace(render_anchor, systems_render, 1)

# Ensure mobile reset touches the new core if switching breakpoints.
old_reset = "document.querySelectorAll('[data-visual],[data-page-copy],.assembly-axis,.proof-note,.exploded img').forEach(el=>{"
new_reset = "document.querySelectorAll('[data-visual],[data-page-copy],.assembly-axis,.proof-note,.exploded img,[data-systems-core]').forEach(el=>{"
if old_reset in s:
    s = s.replace(old_reset, new_reset, 1)

checks = [
    '/* Systems live circuit v9 */',
    'class="systems-experience"',
    'class="systems-circuit"',
    'data-systems-core',
    'const systemExperience=',
    "if(active==='system'&&systemExperience&&systemSticky)",
    'systemsTimelineFill.style.transform',
]
for check in checks:
    if check not in s:
        raise RuntimeError(f'missing systems v9 component: {check}')
if 'Contained fluid circuit</div>\n<h2>Fresh in.' in s:
    raise RuntimeError('legacy systems page survived')

INDEX.write_text(s)
print('systems live circuit v9 complete')
