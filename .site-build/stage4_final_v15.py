from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'website/index.html'
s = INDEX.read_text()

# Stage 4 is deliberately subtractive: one idea, one focal point, one supporting sentence.
copy = {
    'A contained facial-cleansing wearable that delivers, moves and recovers fluid hands-free.':
        'A hands-free facial-cleansing wearable.',
    'Fresh moves in.<br>Used fluid moves out.': 'Fresh in.<br>Used out.',
    'Fresh water and cleanser move toward the face. Recovered liquid returns to containment through a separate path.':
        'Water and cleanser move toward the face. Recovered liquid returns separately.',
    'Recovered fluid routes to a removable cartridge. Recovery and servicing still require physical validation.':
        'Recovered liquid returns to a removable cartridge.',
    'Recovery, hygiene and servicing remain unvalidated.': 'Recovery remains under validation.',
    'The digital assembly resolves the major layers and interfaces. Fit, flow, airway, motion, recovery, comfort, durability, hygiene and safety still require physical evidence.':
        'Fit, flow, airway, motion and recovery still require physical evidence.',
    'Every layer still requires physical validation.': '',
    'No paid pre-orders. Product visuals may change as physical evidence closes.': '',
}
for old, new in copy.items():
    s = s.replace(old, new)

# Cards/readouts repeat the visual story and waste attention.
s = re.sub(r'<div class="systems-facts">.*?</div>\s*', '', s, flags=re.S)
s = re.sub(r'<div class="detail-grid">.*?</div>\s*</div>', '</div>', s, flags=re.S)
s = re.sub(r'<div class="proof-note">.*?</div>', '', s, flags=re.S)

# Section/page numbers are not useful once navigation and scroll position establish context.
s = re.sub(r'<div class="section-tag">.*?</div>\s*', '', s, flags=re.S)
s = re.sub(r'<div class="systems-step[^>]*>.*?</div>\s*', '', s, flags=re.S)

# Give every current visual a stable final asset slot so Stage 3 replacements are one-line swaps.
s = s.replace('class="systems-flow-visual"', 'class="systems-flow-visual" data-asset-slot="manifold"', 1)
s = s.replace('class="systems-motion-visual"', 'class="systems-motion-visual" data-asset-slot="motion-chassis"', 1)
s = s.replace('class="primary" src="https://masck-one.vercel.app/images/chapter-cartridge-v2.webp"',
              'class="primary" data-asset-slot="cartridge-hero" src="https://masck-one.vercel.app/images/chapter-cartridge-v2.webp"', 1)
for cls, slot in [
    ('layer-shell','explode-shell'),
    ('layer-manifold','explode-distribution'),
    ('layer-interface','explode-interface'),
    ('layer-chassis','explode-chassis'),
    ('layer-cartridge','explode-cartridge'),
]:
    s = s.replace(f'class="{cls}"', f'class="{cls}" data-asset-slot="{slot}"', 1)

# Silent ending: wordmark, year, return. Remove the explanatory footer essay.
s = re.sub(r'<div class="closing-statement">.*?</div>\s*', '', s, flags=re.S)
s = re.sub(r'<div class="closing-meta">.*?</div>\s*', '', s, flags=re.S)
if 'class="closing-year"' not in s:
    s = s.replace('<button type="button" class="closing-return"', '<div class="closing-year" aria-hidden="true">2026</div>\n<button type="button" class="closing-return"', 1)

# One reusable shader canvas and one SVG displacement filter. They are decorative and fail closed.
if 'id="brand-field"' not in s:
    s = s.replace('<main id="main-content"', '<canvas id="brand-field" class="brand-field" aria-hidden="true"></canvas>\n<svg class="fx-defs" aria-hidden="true" width="0" height="0"><filter id="windText"><feTurbulence id="windNoise" type="fractalNoise" baseFrequency="0.007 0.035" numOctaves="2" seed="8"/><feDisplacementMap id="windDisplace" in="SourceGraphic" scale="0" xChannelSelector="R" yChannelSelector="G"/></filter></svg>\n<main id="main-content"', 1)

css = r'''
/* Stage 4 final composition + interaction v15 */
:root{--stage4-display:"Instrument Serif",serif;--stage4-body:Manrope,system-ui,sans-serif}
.header{border-color:rgba(24,33,28,.10)!important;background:rgba(247,249,246,.76)!important;background-image:none!important;animation:none!important;box-shadow:0 10px 34px rgba(24,33,28,.045)!important}
.nav-progress{height:1px!important;background:rgba(24,33,28,.08)!important}.nav-progress-fill{background:currentColor!important;box-shadow:none!important;opacity:.48}
.hero-copy{top:14.5vh!important;width:min(690px,48vw)!important}
.hero h1{font-family:var(--stage4-display)!important;font-size:clamp(88px,10.25vw,174px)!important;line-height:.82!important;letter-spacing:-.066em!important;max-width:760px!important}
.hero h1 span+span{margin-left:.075em!important;font-style:italic}
.hero-copy p{border:0!important;padding:0!important;margin-top:28px!important;max-width:29ch!important;font:500 clamp(15px,1.15vw,18px)/1.48 var(--stage4-body)!important;letter-spacing:-.018em!important;opacity:.72!important}
.hero-meta,.hero-bottom{display:none!important}
.band{opacity:.86}.band-track{animation-duration:46s!important}.band.one .band-track{animation-duration:52s!important}

/* Handoff: keep all three words in-frame and make the object the focal point. */
.mask-orbit-overlay{width:min(84vw,1040px)!important;height:min(58vh,560px)!important;left:50%!important;top:50%!important;overflow:visible!important;transform:translate(-50%,-50%)!important}
.mask-orbit-node span{font-family:var(--stage4-display)!important;font-size:clamp(50px,6.5vw,100px)!important;letter-spacing:-.055em!important;white-space:nowrap!important}
.handoff-halo{opacity:.18!important}.handoff-page{overflow:hidden!important}

/* Systems: text does not compete with visual explanation. */
.systems-facts,.systems-readout,.systems-step{display:none!important}
.systems-copy{width:min(46vw,650px)!important}
.systems-copy h2{font-family:var(--stage4-display)!important;font-size:clamp(72px,8.2vw,132px)!important;line-height:.83!important;letter-spacing:-.062em!important;max-width:680px!important}
.systems-copy>p{max-width:31ch!important;font:500 clamp(15px,1.12vw,18px)/1.52 var(--stage4-body)!important;letter-spacing:-.016em!important;opacity:.66!important}
.systems-copy-flow{left:var(--pad)!important;right:auto!important}.systems-copy-motion{left:auto!important;right:var(--pad)!important}
.systems-flow-visual{left:43%!important;width:53vw!important;transform-origin:56% 50%!important}
.systems-motion-visual{left:3.5vw!important;width:52vw!important;transform-origin:42% 50%!important}
.systems-evidence{font-size:9px!important;line-height:1.45!important;letter-spacing:.02em!important;text-transform:none!important;opacity:.42!important}
.systems-word{opacity:.025!important;letter-spacing:-.07em!important}
.systems-timeline{opacity:.34!important}

/* Proof: larger useful imagery, almost no supporting UI. */
.section-tag,.detail-grid,.page-index,.proof-note{display:none!important}
.page{grid-template-columns:minmax(330px,.82fr) 1.18fr!important;gap:3.5vw!important;padding-top:96px!important}
.page-copy{max-width:650px!important}.page h2{font-family:var(--stage4-display)!important;font-size:clamp(72px,8.4vw,134px)!important;line-height:.82!important;letter-spacing:-.064em!important;max-width:720px!important}
.page-copy>p{max-width:31ch!important;margin-top:28px!important;font:500 clamp(15px,1.12vw,18px)/1.52 var(--stage4-body)!important;letter-spacing:-.016em!important;opacity:.68!important}
.page .visual{height:min(82vh,820px)!important;transform:translateY(3vh)}
.page.dark .visual-stage{transform:translateY(-2vh) scale(1.18)!important}.page.dark .visual-stage .primary{max-height:70vh!important}
.page.clay .visual.exploded{transform:translateY(1vh) scale(1.08)!important}
.evidence-line{right:var(--pad)!important;bottom:24px!important;max-width:360px!important;font:400 9px/1.45 DM Mono,monospace!important;letter-spacing:.02em!important;text-transform:none!important;opacity:.48!important}
.evidence-line:empty{display:none!important}

/* Silent end. */
.closing-statement,.closing-meta,.closing-kicker{display:none!important}.closing-chamber{min-height:100svh!important;place-items:center!important}
.closing-wordmark{font-family:var(--stage4-display)!important;font-size:clamp(112px,18vw,300px)!important;line-height:.68!important;letter-spacing:-.075em!important}
.closing-year{position:absolute;left:var(--pad);bottom:28px;font:400 10px/1 DM Mono,monospace;letter-spacing:.16em;opacity:.44}
.closing-return{bottom:22px!important}

/* A single low-cost WebGL field changes personality by chamber. */
.brand-field{position:fixed;z-index:0;inset:0;width:100vw;height:100vh;pointer-events:none;opacity:.28;mix-blend-mode:soft-light}
.view{position:relative;z-index:1}.fx-defs{position:absolute;pointer-events:none}
[data-wind]{transition:transform .7s cubic-bezier(.16,1,.3,1),text-shadow .7s ease;transform-origin:50% 70%;will-change:transform,filter}
[data-wind].wind-active{filter:url(#windText);text-shadow:22px 0 38px rgba(255,255,255,.08),-14px 0 34px rgba(24,33,28,.055)}

/* Explicit future Stage-3 asset contract. */
[data-asset-slot]{--asset-ready:1}

@media(max-width:900px){
  .brand-field{display:none!important}
  .hero-copy{top:14vh!important;width:auto!important;right:22px!important}.hero h1{font-size:clamp(60px,17vw,82px)!important;line-height:.84!important}
  .hero-copy p{font-size:16px!important;max-width:24ch!important;margin-top:22px!important}
  .mask-orbit-overlay{width:92vw!important;height:52vh!important}.mask-orbit-node span{font-size:clamp(38px,12vw,64px)!important}
  .systems-copy{width:auto!important;left:24px!important;right:24px!important}.systems-copy h2,.page h2{font-size:clamp(52px,15vw,76px)!important;line-height:.86!important}
  .systems-copy>p,.page-copy>p{font-size:16px!important;max-width:27ch!important}
  .systems-flow-visual,.systems-motion-visual{left:5vw!important;width:90vw!important}
  .page{grid-template-columns:1fr!important;gap:18px!important;padding:104px 24px 58px!important}.page .visual{height:48svh!important;transform:none!important}.page.dark .visual-stage,.page.clay .visual.exploded{transform:none!important}
  .evidence-line{left:24px!important;right:24px!important;text-align:left!important;bottom:18px!important}
  [data-wind]{filter:none!important;transform:none!important}
  .closing-wordmark{font-size:clamp(82px,28vw,132px)!important}.closing-year{left:24px!important}
}
@media(prefers-reduced-motion:reduce){.brand-field{display:none!important}[data-wind]{filter:none!important;transform:none!important}}
/* End Stage 4 final composition + interaction v15 */
'''
if '/* Stage 4 final composition + interaction v15 */' not in s:
    s = s.replace('\n</style>\n</head>', css + '\n</style>\n</head>', 1)

js = r'''
/* Stage 4 interaction v15 */
(()=>{
  const reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;
  const canHover=matchMedia('(hover:hover) and (pointer:fine)').matches;
  const windNoise=document.getElementById('windNoise');
  const windDisplace=document.getElementById('windDisplace');
  document.querySelectorAll('.hero h1 span,.systems-copy h2,.page-copy h2,.closing-wordmark').forEach(el=>{
    el.dataset.wind='';
    if(!canHover||reduce)return;
    el.addEventListener('pointerenter',()=>{el.classList.add('wind-active');windDisplace?.setAttribute('scale','8')});
    el.addEventListener('pointermove',e=>{
      const r=el.getBoundingClientRect(),nx=(e.clientX-r.left)/Math.max(1,r.width)-.5,ny=(e.clientY-r.top)/Math.max(1,r.height)-.5;
      el.style.transform=`translate3d(${nx*7}px,${ny*2}px,0) skewX(${nx*1.4}deg)`;
      windDisplace?.setAttribute('scale',String(7+Math.abs(nx)*18));
      windNoise?.setAttribute('baseFrequency',`${.006+Math.abs(ny)*.004} ${.03+Math.abs(nx)*.018}`);
    });
    el.addEventListener('pointerleave',()=>{el.classList.remove('wind-active');el.style.transform='';windDisplace?.setAttribute('scale','0')});
  });

  if(reduce||innerWidth<901)return;
  const canvas=document.getElementById('brand-field');
  const gl=canvas?.getContext('webgl',{alpha:true,antialias:false,powerPreference:'low-power'});
  if(!gl||!canvas)return;
  const vert=`attribute vec2 p;varying vec2 v;void main(){v=p*.5+.5;gl_Position=vec4(p,0.,1.);}`;
  const frag=`precision mediump float;varying vec2 v;uniform vec2 r;uniform vec2 m;uniform float t;uniform float mode;
  float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
  float noise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);return mix(mix(hash(i),hash(i+vec2(1,0)),f.x),mix(hash(i+vec2(0,1)),hash(i+vec2(1,1)),f.x),f.y);}
  void main(){vec2 uv=(v-.5)*vec2(r.x/r.y,1.);float n=noise(uv*3.2+vec2(t*.035,-t*.018));float a=0.;vec3 c=vec3(.75,.84,.82);
    if(mode<.5){float d=abs(uv.y+.14*sin(uv.x*3.+t*.12)+.08*n);a=smoothstep(.18,0.,d)*.17;c=vec3(.78,.87,.88);}
    else if(mode<1.5){float f1=abs(uv.y-.22*sin(uv.x*3.5+t*.18));float f2=abs(uv.y+.18*sin(uv.x*2.6-t*.15));a=(smoothstep(.095,0.,f1)+smoothstep(.075,0.,f2))*.12;c=mix(vec3(.75,.82,.73),vec3(.78,.65,.56),n);}
    else{float scan=smoothstep(.08,0.,abs(uv.x-(m.x-.5)*1.2));float grain=smoothstep(.72,1.,n);a=scan*.10+grain*.025;c=vec3(.90,.78,.69);}
    gl_FragColor=vec4(c,a);
  }`;
  const shader=(type,src)=>{const sh=gl.createShader(type);gl.shaderSource(sh,src);gl.compileShader(sh);return sh};
  const pr=gl.createProgram();gl.attachShader(pr,shader(gl.VERTEX_SHADER,vert));gl.attachShader(pr,shader(gl.FRAGMENT_SHADER,frag));gl.linkProgram(pr);gl.useProgram(pr);
  const b=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,b);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,-1,1,1,-1,1,1]),gl.STATIC_DRAW);const loc=gl.getAttribLocation(pr,'p');gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,2,gl.FLOAT,false,0,0);
  const ur=gl.getUniformLocation(pr,'r'),um=gl.getUniformLocation(pr,'m'),ut=gl.getUniformLocation(pr,'t'),uMode=gl.getUniformLocation(pr,'mode');let mx=.5,my=.5;
  addEventListener('pointermove',e=>{mx=e.clientX/innerWidth;my=1-e.clientY/innerHeight},{passive:true});
  const size=()=>{const d=Math.min(devicePixelRatio||1,1.5);canvas.width=Math.round(innerWidth*d);canvas.height=Math.round(innerHeight*d);gl.viewport(0,0,canvas.width,canvas.height)};size();addEventListener('resize',size,{passive:true});
  const draw=now=>{const active=document.querySelector('.view.active')?.dataset.view;const mode=active==='system'?1:active==='proof'?2:0;gl.uniform2f(ur,canvas.width,canvas.height);gl.uniform2f(um,mx,my);gl.uniform1f(ut,now*.001);gl.uniform1f(uMode,mode);gl.drawArrays(gl.TRIANGLES,0,6);requestAnimationFrame(draw)};requestAnimationFrame(draw);
})();
/* End Stage 4 interaction v15 */
'''
if '/* Stage 4 interaction v15 */' not in s:
    s = s.replace('\n</body>', f'\n<script>\n{js}\n</script>\n</body>', 1)

# Fail closed if the attention hierarchy regresses.
for forbidden in [
    'class="systems-facts"', 'class="detail-grid"', 'class="section-tag"',
    'class="systems-step', 'class="proof-note"', 'Built toward evidence.',
    'No paid pre-orders. Product visuals may change as physical evidence closes.'
]:
    if forbidden in s:
        raise RuntimeError(f'Stage 4 restraint regression: {forbidden}')

assert 'A hands-free facial-cleansing wearable.' in s
assert 'Fresh in.<br>Used out.' in s
assert 'Recovered liquid returns to a removable cartridge.' in s
assert 'Fit, flow, airway, motion and recovery still require physical evidence.' in s
assert s.count('data-asset-slot=') >= 7
assert s.count('id="brand-field"') == 1
assert s.count('id="windText"') == 1
assert '/* Stage 4 final composition + interaction v15 */' in s
assert '/* Stage 4 interaction v15 */' in s
assert s.count('mask-journey hero-mask-single') == 1
assert s.count('class="hero-mask-art"') == 1

INDEX.write_text(s)
print('stage 4 final interaction v15 complete')
