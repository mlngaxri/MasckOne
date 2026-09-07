from __future__ import annotations

"""Prompt 18 website transform: one cohesive, truth-bounded customer use journey."""

from hashlib import sha256
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "website" / "index.html"
TRUTH = ROOT / "website" / "use-journey-v18-truth.json"
MARKER = "<!-- Product use journey v18 -->"
CSS_MARKER = "/* Product use journey v18 */"

SOURCES = {
    "website_main_at_build": os.environ.get("MASCK_WEBSITE_BUILD_SHA", "UNKNOWN"),
    "fresh_water_head": "22d2e5baccbcfa56aa4a70e4e4dd59693e15affd",
    "cleanser_graph_head": "8d5762f35c0b64b736648ef3541377b43a168952",
    "hmi_head": "7b32c674860cab87cbdd1f7e3303a4ce53515e95",
    "retention_release_guard_head": "fb586cc1ea1cde92526417593f9e5aa990d2ae4f",
    "occipital_yokes_head": "25686766238b66ecf900009042d721c08e042592",
    "waste_cartridge_head": "4da053e57534c98617b9e8abfae7a35436a3718c",
    "dry_side_head": "fa017c8379dabaefeecf53bf770858bebfde3067",
    "prompt17_manifest_blob": "dcb3338bd0984d36414cac03a765c807b2b04492",
}

STAGES = [
    {
        "key": "prepare",
        "label": "PREPARE",
        "view": "front",
        "copy": "Prepare water and cleanser before wearing.",
        "dominant_action": "ABSTRACT_SUPPLY_PREPARATION_NO_FINISHED_REFILL_HARDWARE",
        "truth": "Fresh-water fill and cleanser service architecture exist digitally, but finished customer refill closures and complete product service motion remain unresolved.",
    },
    {
        "key": "wear",
        "label": "WEAR",
        "view": "side",
        "copy": "Place the shell to the face, then bring the rear supports into position.",
        "dominant_action": "NOMINAL_PLACEMENT_WITH_CURRENT_BILATERAL_REAR_SUPPORT_GEOMETRY",
        "truth": "Current retention geometry is digital; fit range, comfort, preload, hair interaction and population validation remain open.",
    },
    {
        "key": "choose",
        "label": "CHOOSE",
        "view": "front",
        "copy": "The physical control area is reserved for choosing and activation; final mapping remains open.",
        "dominant_action": "CONTROL_CAPACITY_REGION_TOUCH_WITHOUT_FAKE_BUTTON_TRAVEL",
        "truth": "The primary physical HMI capacity region is registered, but control count, function mapping, switch technology, travel, force and tactile response are not frozen.",
    },
    {
        "key": "clean",
        "label": "CLEAN",
        "view": "front",
        "copy": "The cycle supplies, moves and recovers fluid while you wear it.",
        "dominant_action": "CUSTOMER_LEVEL_SUPPLY_MOVE_RECOVER_CYCLE",
        "truth": "The website reuses the established supply, move and recover language without repeating engineering routing detail.",
    },
    {
        "key": "remove",
        "label": "REMOVE",
        "view": "side",
        "copy": "Pull the right-side release, then lift the device away.",
        "dominant_action": "RIGHT_SIDE_RELEASE_PULL_DIRECTION_PLUS_NOMINAL_LIFT_AWAY",
        "truth": "The current digital right-side release uses a captive one-hand pull in wearer +X; release force, time, wet usability and complete whole-head removal remain unvalidated.",
    },
    {
        "key": "service",
        "label": "SERVICE",
        "view": "rear",
        "copy": "Routine access begins at the rear service cover.",
        "dominant_action": "IDENTIFY_REAL_VISIBLE_REAR_SERVICE_COVER_WITHOUT_FAKE_INTERNAL_TUTORIAL",
        "truth": "The visible rear service cover belongs to the current exterior candidate. Internal waste and supply service geometry is digital and continuous customer service motion remains open.",
    },
    {
        "key": "recharge",
        "label": "RECHARGE",
        "view": "rear",
        "copy": "Charging is reserved at the left-lower power interface; connector hardware is not selected.",
        "dominant_action": "LOCATE_CHARGING_RESERVATION_WITHOUT_CONNECTOR_CABLE_OR_DOCK",
        "truth": "The dry-side candidate reserves a left-lower wall crossing for charging, while connector type, retention, ingress and electrical validation remain unresolved.",
    },
]

ASSETS = {
    "front": "images/masck-inspection-front-3q-v17c.webp",
    "side": "images/masck-inspection-side-rear-v17c.webp",
    "rear": "images/masck-inspection-rear-3q-v17c.webp",
}


def desktop_gestures() -> str:
    return """
<div class="j18-gesture j18-prepare" data-j18-gesture="prepare" aria-hidden="true">
  <div class="j18-supply j18-water"><span>Water</span></div><div class="j18-supply j18-cleanser"><span>Cleanser</span></div><i class="j18-converge a"></i><i class="j18-converge b"></i>
</div>
<div class="j18-gesture j18-wear" data-j18-gesture="wear" aria-hidden="true">
  <div class="j18-headref"><i></i></div><div class="j18-wear-arrow"><span>Place</span></div><div class="j18-rear-arc"><span>Rear supports</span></div>
</div>
<div class="j18-gesture j18-choose" data-j18-gesture="choose" aria-hidden="true">
  <div class="j18-control-region"><i></i><span>Physical control area<br><b>Mapping in development</b></span></div><div class="j18-fingertip"></div>
</div>
<div class="j18-gesture j18-clean" data-j18-gesture="clean" aria-hidden="true">
  <div class="j18-cycle-ring"></div><span class="j18-cycle-word supply">Supply</span><span class="j18-cycle-word move">Move</span><span class="j18-cycle-word recover">Recover</span>
</div>
<div class="j18-gesture j18-remove" data-j18-gesture="remove" aria-hidden="true">
  <div class="j18-release-marker"><i></i><span>Right release</span></div><div class="j18-release-arrow"><span>Pull +X</span></div>
</div>
<div class="j18-gesture j18-service" data-j18-gesture="service" aria-hidden="true">
  <div class="j18-service-marker"><i></i><span>Rear service cover</span></div><div class="j18-access-line"><span>Access</span></div>
</div>
<div class="j18-gesture j18-recharge" data-j18-gesture="recharge" aria-hidden="true">
  <div class="j18-charge-marker"><i></i><span>Left-lower charge reservation<br><b>Connector open</b></span></div>
</div>
"""


def mobile_action(stage: dict[str, str]) -> str:
    key = stage["key"]
    if key == "prepare":
        return '<div class="j18m-action prepare" aria-hidden="true"><span>Water</span><i></i><span>Cleanser</span></div>'
    if key == "wear":
        return '<div class="j18m-action wear" aria-hidden="true"><i></i><span>Place / support</span></div>'
    if key == "choose":
        return '<div class="j18m-action choose" aria-hidden="true"><i></i><span>Physical control area</span></div>'
    if key == "clean":
        return '<div class="j18m-action clean" aria-hidden="true"><span>Supply</span><span>Move</span><span>Recover</span></div>'
    if key == "remove":
        return '<div class="j18m-action remove" aria-hidden="true"><i></i><span>Right release / pull +X</span></div>'
    if key == "service":
        return '<div class="j18m-action service" aria-hidden="true"><i></i><span>Rear service cover</span></div>'
    if key == "recharge":
        return '<div class="j18m-action recharge" aria-hidden="true"><i></i><span>Charge reservation / connector open</span></div>'
    raise ValueError(key)


def build_html() -> str:
    rail = "".join(
        f'<button type="button" data-j18-step="{i}" aria-label="Show {stage["label"].title()} stage"><i>{i + 1:02d}</i><span>{stage["label"]}</span></button>'
        for i, stage in enumerate(STAGES)
    )
    mobile = "".join(
        f'''<article class="journey18-mobile-state" data-j18-mobile-stage="{stage["key"]}">
  <div class="j18m-copy"><span>{i + 1:02d} / {len(STAGES):02d}</span><h3>{stage["label"]}</h3><p>{stage["copy"]}</p></div>
  <div class="j18m-visual"><img src="{ASSETS[stage["view"]]}" alt="" loading="lazy" decoding="async" draggable="false">{mobile_action(stage)}</div>
</article>'''
        for i, stage in enumerate(STAGES)
    )
    first = STAGES[0]
    return f'''
{MARKER}
<section class="use-journey18" aria-label="MASCK ONE normal use" data-use-journey18 data-version="v18" data-stage="{first["key"]}" data-active-index="0" data-source-main="{SOURCES["website_main_at_build"]}">
  <div class="journey18-desktop">
    <div class="journey18-sticky">
      <div class="j18-copy">
        <div class="j18-kicker">Normal use</div>
        <h2>One routine.</h2>
        <div class="j18-active-copy" aria-live="polite">
          <span data-j18-count>01 / {len(STAGES):02d}</span>
          <h3 data-j18-label>{first["label"]}</h3>
          <p data-j18-copy>{first["copy"]}</p>
        </div>
      </div>
      <div class="j18-visual" data-j18-visual>
        <div class="j18-glow" aria-hidden="true"></div>
        <img class="j18-product active" data-j18-view="front" src="{ASSETS["front"]}" alt="MASCK ONE front three-quarter view" decoding="async" draggable="false">
        <img class="j18-product" data-j18-view="side" src="{ASSETS["side"]}" alt="MASCK ONE side and rear view" loading="lazy" decoding="async" draggable="false">
        <img class="j18-product" data-j18-view="rear" src="{ASSETS["rear"]}" alt="MASCK ONE rear three-quarter view" loading="lazy" decoding="async" draggable="false">
        {desktop_gestures()}
      </div>
      <nav class="j18-rail" aria-label="Normal use sequence">{rail}</nav>
      <div class="j18-truth"><span>Current digital architecture</span><span>Refill closures, fit range, release performance, control mapping, full service motion and charging connector remain in development.</span></div>
      <div class="j18-progress" aria-hidden="true"></div>
    </div>
  </div>
  <div class="journey18-mobile">
    <header class="j18m-intro"><div class="j18-kicker">Normal use</div><h2>One routine.</h2><p>Prepare it, wear it, let it work, then reset it for next time.</p></header>
    {mobile}
    <footer class="j18m-truth"><span>Current digital architecture</span><p>Refill closures, fit range, release performance, control mapping, full service motion and charging connector remain in development.</p></footer>
  </div>
</section>
'''


CSS = r'''

/* Product use journey v18 */
.use-journey18{position:relative;height:720svh;background:#18211c;color:#f7f7f2;border-top:1px solid rgba(247,247,242,.08);isolation:isolate}
.journey18-desktop{height:100%}.journey18-mobile{display:none}.journey18-sticky{position:sticky;top:0;height:100svh;min-height:680px;overflow:hidden;background:radial-gradient(circle at 66% 49%,rgba(216,230,224,.13),transparent 31%),linear-gradient(145deg,#18211c 0%,#1d2821 62%,#23302a 100%)}
.journey18-sticky:after{content:"";position:absolute;inset:0;pointer-events:none;background:linear-gradient(90deg,rgba(24,33,28,.18),transparent 38%,transparent 75%,rgba(24,33,28,.12));z-index:1}
.j18-copy{position:absolute;z-index:8;left:max(var(--pad),5vw);top:50%;width:min(410px,30vw);transform:translateY(-50%)}
.j18-kicker{display:flex;align-items:center;gap:11px;margin-bottom:18px;font:400 8px/1 DM Mono,monospace;letter-spacing:.145em;text-transform:uppercase;color:rgba(247,247,242,.48)}
.j18-kicker:before{content:"";width:29px;height:1px;background:currentColor;opacity:.55}
.j18-copy h2,.j18m-intro h2{margin:0;font:400 clamp(66px,6.7vw,104px)/.82 Instrument Serif,serif;letter-spacing:-.055em;color:#f7f7f2}
.j18-active-copy{margin-top:30px;padding-top:14px;border-top:1px solid rgba(247,247,242,.17);max-width:370px;min-height:132px}
.j18-active-copy>span{font:400 6.5px/1 DM Mono,monospace;letter-spacing:.1em;text-transform:uppercase;color:rgba(247,247,242,.38)}
.j18-active-copy h3{margin:10px 0 9px;font:400 clamp(24px,2vw,31px)/1 Instrument Serif,serif;letter-spacing:-.035em}
.j18-active-copy p{margin:0;max-width:360px;font:500 clamp(12.5px,.96vw,15px)/1.62 Manrope,system-ui,sans-serif;letter-spacing:-.014em;color:rgba(247,247,242,.66)}
.j18-visual{position:absolute;z-index:4;left:65%;top:48.5%;width:min(61vw,850px);aspect-ratio:1;transform:translate(-50%,-50%)}
.j18-glow{position:absolute;left:50%;top:52%;width:72%;aspect-ratio:1;transform:translate(-50%,-50%);border-radius:50%;background:radial-gradient(circle,rgba(255,255,255,.1),rgba(210,228,220,.04) 48%,transparent 72%);filter:blur(4px)}
.j18-product{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;opacity:0;transform:scale(.985);filter:drop-shadow(0 28px 34px rgba(0,0,0,.17)) drop-shadow(0 65px 82px rgba(0,0,0,.18));transition:opacity .55s var(--ease),transform .9s var(--ease);pointer-events:none}
.j18-product.active{opacity:1;transform:scale(1)}
.j18-gesture{position:absolute;inset:0;z-index:6;opacity:0;pointer-events:none;transition:opacity .42s var(--ease)}.j18-gesture.active{opacity:1}
.j18-supply{position:absolute;width:96px;height:96px;border:1px solid rgba(247,247,242,.18);border-radius:50%;display:grid;place-items:center;background:rgba(247,247,242,.035);backdrop-filter:blur(8px);font:400 7px/1 DM Mono,monospace;letter-spacing:.11em;text-transform:uppercase;color:rgba(247,247,242,.72)}
.j18-water{left:8%;top:33%}.j18-cleanser{right:6%;top:61%}.j18-water:after,.j18-cleanser:after{content:"";position:absolute;inset:18px;border-radius:50%;background:radial-gradient(circle at 38% 32%,rgba(210,232,241,.5),rgba(126,174,193,.12) 58%,transparent 62%)}
.j18-cleanser:after{background:radial-gradient(circle at 38% 32%,rgba(229,211,188,.5),rgba(185,126,101,.12) 58%,transparent 62%)}.j18-supply span{z-index:1}
.j18-converge{position:absolute;height:1px;width:17%;background:linear-gradient(90deg,rgba(247,247,242,.08),rgba(247,247,242,.44),rgba(247,247,242,.08));transform-origin:left}.j18-converge.a{left:20%;top:43%;transform:rotate(8deg)}.j18-converge.b{right:18%;top:67%;transform:rotate(192deg)}
.j18-headref{position:absolute;left:35%;top:21%;width:32%;height:56%;border:1px solid rgba(247,247,242,.15);border-radius:49% 48% 45% 50%;transform:rotate(-3deg);opacity:.8}.j18-headref i{position:absolute;right:-8%;top:46%;width:17%;height:12%;border:1px solid rgba(247,247,242,.14);border-left:0;border-radius:0 80% 80% 0}
.j18-wear-arrow{position:absolute;left:17%;top:47%;width:18%;height:1px;background:rgba(247,247,242,.36)}.j18-wear-arrow:after{content:"";position:absolute;right:-1px;top:-3px;width:6px;height:6px;border-top:1px solid rgba(247,247,242,.52);border-right:1px solid rgba(247,247,242,.52);transform:rotate(45deg)}.j18-wear-arrow span,.j18-rear-arc span{position:absolute;bottom:9px;left:0;font:400 6px/1 DM Mono,monospace;letter-spacing:.1em;text-transform:uppercase;color:rgba(247,247,242,.52);white-space:nowrap}
.j18-rear-arc{position:absolute;right:11%;top:43%;width:17%;height:24%;border-right:1px solid rgba(247,247,242,.28);border-radius:0 80px 80px 0}.j18-rear-arc span{left:auto;right:0;bottom:-18px;text-align:right}
.j18-control-region{position:absolute;left:71.461%;top:40.655%;width:14px;height:14px;transform:translate(-50%,-50%)}.j18-control-region i{position:absolute;inset:2px;border:1px solid rgba(247,247,242,.76);border-radius:50%;background:rgba(247,247,242,.12)}.j18-control-region:before,.j18-control-region:after{content:"";position:absolute;border:1px solid rgba(247,247,242,.22);border-radius:50%;inset:-7px}.j18-control-region:after{inset:-15px;opacity:.46}.j18-control-region span{position:absolute;left:44px;top:-13px;width:176px;padding-left:10px;border-left:1px solid rgba(247,247,242,.2);font:400 6.5px/1.55 DM Mono,monospace;letter-spacing:.08em;text-transform:uppercase;color:rgba(247,247,242,.62)}.j18-control-region span b{font-weight:400;color:rgba(247,247,242,.34)}
.j18-fingertip{position:absolute;left:79%;top:31%;width:38px;height:38px;border-radius:50%;border:1px solid rgba(247,247,242,.17);background:radial-gradient(circle at 40% 40%,rgba(247,247,242,.18),rgba(247,247,242,.025) 66%,transparent 70%);transform:translate(-50%,-50%)}.j18-fingertip:after{content:"";position:absolute;left:-48px;top:33px;width:54px;height:1px;background:rgba(247,247,242,.22);transform:rotate(-28deg);transform-origin:right}
.j18-cycle-ring{position:absolute;left:50%;top:51%;width:59%;aspect-ratio:1;transform:translate(-50%,-50%);border:1px solid rgba(247,247,242,.13);border-radius:50%}.j18-cycle-ring:before{content:"";position:absolute;inset:7%;border:1px dashed rgba(247,247,242,.17);border-radius:50%;animation:j18Turn 18s linear infinite}.j18-cycle-word{position:absolute;font:400 7px/1 DM Mono,monospace;letter-spacing:.13em;text-transform:uppercase;color:rgba(247,247,242,.7)}.j18-cycle-word.supply{left:15%;top:48%}.j18-cycle-word.move{left:48%;top:17%}.j18-cycle-word.recover{right:9%;top:59%}@keyframes j18Turn{to{transform:rotate(360deg)}}
.j18-release-marker{position:absolute;left:74%;top:53%;width:12px;height:12px;transform:translate(-50%,-50%)}.j18-release-marker i,.j18-service-marker i,.j18-charge-marker i{position:absolute;inset:1px;border:1px solid rgba(247,247,242,.7);border-radius:50%}.j18-release-marker span,.j18-service-marker span,.j18-charge-marker span{position:absolute;left:31px;top:-6px;width:max-content;font:400 6.5px/1.5 DM Mono,monospace;letter-spacing:.08em;text-transform:uppercase;color:rgba(247,247,242,.62)}
.j18-release-arrow{position:absolute;left:75%;top:57%;width:15%;height:1px;background:rgba(247,247,242,.44)}.j18-release-arrow:after{content:"";position:absolute;right:0;top:-3px;width:6px;height:6px;border-top:1px solid rgba(247,247,242,.55);border-right:1px solid rgba(247,247,242,.55);transform:rotate(45deg)}.j18-release-arrow span,.j18-access-line span{position:absolute;top:9px;left:0;font:400 6px/1 DM Mono,monospace;letter-spacing:.1em;text-transform:uppercase;color:rgba(247,247,242,.48)}
.j18-service-marker{position:absolute;left:56.655%;top:50.437%;width:12px;height:12px;transform:translate(-50%,-50%)}.j18-service-marker span{left:auto;right:31px;text-align:right}.j18-access-line{position:absolute;left:42%;top:54%;width:13%;height:1px;background:rgba(247,247,242,.3);transform:rotate(24deg);transform-origin:right}.j18-access-line span{transform:rotate(-24deg);transform-origin:left}
.j18-charge-marker{position:absolute;left:39%;top:61%;width:13px;height:13px;transform:translate(-50%,-50%)}.j18-charge-marker i{border-style:dashed}.j18-charge-marker:before{content:"";position:absolute;inset:-9px;border:1px dashed rgba(247,247,242,.18);border-radius:50%}.j18-charge-marker span{left:auto;right:34px;text-align:right}.j18-charge-marker span b{font-weight:400;color:rgba(247,247,242,.34)}
.j18-rail{position:absolute;z-index:9;left:max(var(--pad),5vw);right:max(var(--pad),5vw);bottom:78px;height:48px;display:grid;grid-template-columns:repeat(7,1fr);border-top:1px solid rgba(247,247,242,.15)}.j18-rail button{appearance:none;position:relative;display:grid;grid-template-columns:24px 1fr;align-items:center;gap:7px;padding:0 12px 0 0;border:0;border-right:1px solid rgba(247,247,242,.08);background:transparent;color:rgba(247,247,242,.34);text-align:left;cursor:pointer;transition:color .2s var(--ease),transform .2s var(--ease)}.j18-rail button:last-child{border-right:0}.j18-rail button i{font:400 5.5px/1 DM Mono,monospace;font-style:normal;opacity:.55}.j18-rail button span{font:400 6.5px/1 DM Mono,monospace;letter-spacing:.08em;text-transform:uppercase}.j18-rail button.active{color:rgba(247,247,242,.9)}.j18-rail button.active i{color:#c6cfb9;opacity:1}.j18-rail button:focus-visible{outline:1px solid rgba(247,247,242,.7);outline-offset:4px}@media(hover:hover) and (pointer:fine){.j18-rail button:hover{color:rgba(247,247,242,.8);transform:translateY(-2px)}}
.j18-truth{position:absolute;z-index:9;left:max(var(--pad),5vw);right:max(var(--pad),5vw);bottom:24px;display:flex;justify-content:space-between;gap:30px;padding-top:8px;border-top:1px solid rgba(247,247,242,.09);font:400 5.7px/1.45 DM Mono,monospace;letter-spacing:.07em;text-transform:uppercase;color:rgba(247,247,242,.28)}.j18-truth span:last-child{max-width:650px;text-align:right}.j18-progress{position:absolute;z-index:10;left:0;bottom:0;width:100%;height:2px;background:#c6cfb9;opacity:.46;transform:scaleX(0);transform-origin:left center}
@media(min-width:901px) and (max-width:1120px){.j18-copy{width:31vw}.j18-visual{left:63%;width:64vw}.j18-rail button{grid-template-columns:18px 1fr;padding-right:7px}.j18-rail button span{font-size:5.8px}}
@media(max-width:900px){
  .use-journey18{height:auto;background:linear-gradient(160deg,#18211c,#202b24 68%,#25312b)}.journey18-desktop{display:none}.journey18-mobile{display:block;padding:96px 0 58px}.j18m-intro{padding:0 22px 38px}.j18m-intro .j18-kicker{margin-bottom:14px}.j18m-intro h2{font-size:clamp(54px,16vw,76px)}.j18m-intro>p{margin:20px 0 0;max-width:330px;font-size:12.5px;line-height:1.65;color:rgba(247,247,242,.58)}
  .journey18-mobile-state{position:relative;min-height:76svh;padding:38px 22px 30px;display:grid;grid-template-rows:auto 1fr;border-top:1px solid rgba(247,247,242,.1);overflow:hidden}.j18m-copy{position:relative;z-index:5}.j18m-copy>span{font:400 6px/1 DM Mono,monospace;letter-spacing:.09em;color:rgba(247,247,242,.34)}.j18m-copy h3{margin:9px 0 7px;font:400 clamp(38px,11vw,52px)/.95 Instrument Serif,serif;letter-spacing:-.045em}.j18m-copy p{margin:0;max-width:330px;font-size:12px;line-height:1.58;color:rgba(247,247,242,.59)}.j18m-visual{position:relative;align-self:end;width:min(112vw,560px);aspect-ratio:1;margin:4px 0 -7vw 50%;transform:translateX(-50%)}.j18m-visual img{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;filter:drop-shadow(0 22px 30px rgba(0,0,0,.18)) drop-shadow(0 52px 66px rgba(0,0,0,.18))}.j18m-visual:before{content:"";position:absolute;left:50%;top:53%;width:73%;aspect-ratio:1;transform:translate(-50%,-50%);border-radius:50%;background:radial-gradient(circle,rgba(247,247,242,.08),transparent 68%)}
  .j18m-action{position:absolute;z-index:5;font:400 6px/1.4 DM Mono,monospace;letter-spacing:.08em;text-transform:uppercase;color:rgba(247,247,242,.64)}.j18m-action.prepare{left:9%;right:7%;top:43%;display:flex;justify-content:space-between;align-items:center}.j18m-action.prepare span{width:60px;height:60px;display:grid;place-items:center;border:1px solid rgba(247,247,242,.2);border-radius:50%;background:rgba(247,247,242,.035)}.j18m-action.prepare i{height:1px;flex:1;margin:0 9px;background:linear-gradient(90deg,rgba(247,247,242,.1),rgba(247,247,242,.38),rgba(247,247,242,.1))}.j18m-action.wear{left:12%;top:50%;width:22%;height:1px;background:rgba(247,247,242,.36)}.j18m-action.wear i{position:absolute;right:-1px;top:-3px;width:6px;height:6px;border-top:1px solid rgba(247,247,242,.55);border-right:1px solid rgba(247,247,242,.55);transform:rotate(45deg)}.j18m-action.wear span{position:absolute;left:0;bottom:9px;white-space:nowrap}.j18m-action.choose{left:71.46%;top:40.65%;width:12px;height:12px;transform:translate(-50%,-50%)}.j18m-action.choose i,.j18m-action.remove i,.j18m-action.service i,.j18m-action.recharge i{position:absolute;inset:1px;border:1px solid rgba(247,247,242,.72);border-radius:50%}.j18m-action.choose span{position:absolute;left:28px;top:-5px;width:110px}.j18m-action.clean{left:7%;right:7%;top:24%;display:flex;justify-content:space-between}.j18m-action.clean span{padding-top:7px;border-top:1px solid rgba(247,247,242,.23)}.j18m-action.remove{left:74%;top:53%;width:12px;height:12px}.j18m-action.remove:after{content:"";position:absolute;left:15px;top:6px;width:58px;height:1px;background:rgba(247,247,242,.38)}.j18m-action.remove span{position:absolute;left:20px;top:15px;width:110px}.j18m-action.service{left:56.65%;top:50.43%;width:12px;height:12px}.j18m-action.service span{position:absolute;right:25px;top:-4px;width:100px;text-align:right}.j18m-action.recharge{left:39%;top:61%;width:12px;height:12px}.j18m-action.recharge i{border-style:dashed}.j18m-action.recharge span{position:absolute;right:25px;top:-10px;width:132px;text-align:right}
  .j18m-truth{margin:8px 22px 0;padding-top:16px;border-top:1px solid rgba(247,247,242,.12)}.j18m-truth span{font:400 6px/1 DM Mono,monospace;letter-spacing:.09em;text-transform:uppercase;color:rgba(247,247,242,.36)}.j18m-truth p{margin:9px 0 0;max-width:390px;font-size:10.5px;line-height:1.6;color:rgba(247,247,242,.45)}
}
@media(max-width:390px){.journey18-mobile{padding-top:86px}.journey18-mobile-state{min-height:72svh;padding-left:18px;padding-right:18px}.j18m-intro{padding-left:18px;padding-right:18px}.j18m-visual{width:118vw}.j18m-copy p{max-width:300px}.j18m-truth{margin-left:18px;margin-right:18px}}
@media(prefers-reduced-motion:reduce){.j18-product,.j18-gesture,.j18-rail button{transition:none!important}.j18-cycle-ring:before{animation:none!important}}
'''

JS = r'''
<script>
(() => {
  const chapter = document.querySelector('[data-use-journey18]');
  if (!chapter || chapter.dataset.j18Bound === 'true') return;
  chapter.dataset.j18Bound = 'true';
  const desktop = chapter.querySelector('.journey18-desktop');
  const labels = ['PREPARE','WEAR','CHOOSE','CLEAN','REMOVE','SERVICE','RECHARGE'];
  const copies = [
    'Prepare water and cleanser before wearing.',
    'Place the shell to the face, then bring the rear supports into position.',
    'The physical control area is reserved for choosing and activation; final mapping remains open.',
    'The cycle supplies, moves and recovers fluid while you wear it.',
    'Pull the right-side release, then lift the device away.',
    'Routine access begins at the rear service cover.',
    'Charging is reserved at the left-lower power interface; connector hardware is not selected.'
  ];
  const keys = ['prepare','wear','choose','clean','remove','service','recharge'];
  const views = ['front','side','front','front','side','rear','rear'];
  const products = [...chapter.querySelectorAll('.journey18-desktop [data-j18-view]')];
  const gestures = [...chapter.querySelectorAll('.journey18-desktop [data-j18-gesture]')];
  const steps = [...chapter.querySelectorAll('[data-j18-step]')];
  const label = chapter.querySelector('[data-j18-label]');
  const copy = chapter.querySelector('[data-j18-copy]');
  const count = chapter.querySelector('[data-j18-count]');
  const progress = chapter.querySelector('.j18-progress');
  let active = -1;
  let ticking = false;

  function setStage(index) {
    index = Math.max(0, Math.min(keys.length - 1, index));
    if (index === active) return;
    active = index;
    chapter.dataset.activeIndex = String(index);
    chapter.dataset.stage = keys[index];
    if (label) label.textContent = labels[index];
    if (copy) copy.textContent = copies[index];
    if (count) count.textContent = `${String(index + 1).padStart(2,'0')} / ${String(keys.length).padStart(2,'0')}`;
    products.forEach((img) => img.classList.toggle('active', img.dataset.j18View === views[index]));
    gestures.forEach((item) => item.classList.toggle('active', item.dataset.j18Gesture === keys[index]));
    steps.forEach((step, i) => {
      step.classList.toggle('active', i === index);
      if (i === index) step.setAttribute('aria-current','step'); else step.removeAttribute('aria-current');
    });
  }

  function update() {
    ticking = false;
    if (!desktop || getComputedStyle(desktop).display === 'none') return;
    const rect = chapter.getBoundingClientRect();
    const travel = Math.max(1, chapter.offsetHeight - innerHeight);
    const local = Math.max(0, Math.min(travel, -rect.top));
    const p = local / travel;
    if (progress) progress.style.transform = `scaleX(${p})`;
    setStage(Math.round(p * (keys.length - 1)));
  }

  function onScroll() {
    if (!ticking) {
      ticking = true;
      requestAnimationFrame(update);
    }
  }

  steps.forEach((step, i) => step.addEventListener('click', () => {
    const top = scrollY + chapter.getBoundingClientRect().top;
    const travel = Math.max(1, chapter.offsetHeight - innerHeight);
    const target = top + travel * (i / (keys.length - 1));
    scrollTo({top: target, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
  }));

  addEventListener('scroll', onScroll, {passive:true});
  addEventListener('resize', onScroll, {passive:true});
  setStage(0);
  update();
})();
</script>
'''


def main() -> None:
    html = SITE.read_text(encoding="utf-8")
    if MARKER not in html:
        anchor = '<section class="product-inspection inspection-final-v17c"'
        start = html.find(anchor)
        if start < 0:
            raise RuntimeError("Prompt 17 product inspection anchor missing")
        end = html.find("</section>", start)
        if end < 0:
            raise RuntimeError("Prompt 17 closing section missing")
        end += len("</section>")
        html = html[:end] + "\n" + build_html() + html[end:]
    if CSS_MARKER not in html:
        style_end = html.find("</style>")
        if style_end < 0:
            raise RuntimeError("style closing tag missing")
        html = html[:style_end] + CSS + "\n" + html[style_end:]
    if "data-j18-bound" not in html and "chapter.dataset.j18Bound" not in html:
        body_end = html.rfind("</body>")
        if body_end < 0:
            raise RuntimeError("body closing tag missing")
        html = html[:body_end] + JS + "\n" + html[body_end:]

    SITE.write_text(html, encoding="utf-8")

    asset_hashes = {}
    for key, relative in ASSETS.items():
        path = ROOT / "website" / relative.removeprefix("images/") if False else ROOT / "website" / relative
        if not path.is_file():
            raise RuntimeError(f"missing Prompt 17 asset: {relative}")
        asset_hashes[key] = sha256(path.read_bytes()).hexdigest()

    payload = {
        "schema": "MASCK_ONE_WEBSITE_USE_JOURNEY_V18",
        "sequence": [stage["label"] for stage in STAGES],
        "sequence_semantics": "PREPARE_REPLACES_FILL_AND_CHOOSE_COMBINES_SELECT_PLUS_START_BECAUSE_FINISHED_REFILL_HARDWARE_AND_HMI_MAPPING_ARE_NOT_FROZEN",
        "sources": SOURCES,
        "prompt17_registered_assets_sha256": asset_hashes,
        "stages": STAGES,
        "global_claim_boundary": "Current digital product architecture only. Refill closures, population fit, release performance, final HMI mapping, complete customer service motion and charging connector remain unresolved. No dock, connector, charge duration, refill cap, finished bottle, validated fit range or physical release performance is claimed.",
        "mobile_contract": "VERTICAL_SEQUENCED_STATES_NO_HORIZONTAL_CARD_CAROUSEL",
    }
    TRUTH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
