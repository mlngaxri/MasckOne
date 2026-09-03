from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'website/index.html'
s = INDEX.read_text()

START = '/* Final website closure v13 */'
END = '/* End final website closure v13 */'
s = re.sub(re.escape(START) + r'.*?' + re.escape(END) + r'\n?', '', s, flags=re.S)

# Production metadata: intentionally no social preview image until a canonical
# campaign asset exists.
meta = '''<link rel="canonical" href="https://masck-one-final.vercel.app/" />
<meta name="robots" content="index,follow" />
<meta name="color-scheme" content="light" />
<meta property="og:type" content="website" />
<meta property="og:title" content="MASCK ONE | Cleansing, re-engineered" />
<meta property="og:description" content="A contained facial-cleansing wearable in engineering development." />
<meta property="og:url" content="https://masck-one-final.vercel.app/" />
<meta name="twitter:card" content="summary" />'''
if '<link rel="canonical"' not in s:
    s = s.replace('<meta name="description" content="MASCK ONE is a contained-fluid facial cleansing system in engineering development." />',
                  '<meta name="description" content="MASCK ONE is a contained-fluid facial cleansing system in engineering development." />\n' + meta, 1)

# A real skip target for keyboard/screen-reader navigation.
s = s.replace('<main>', '<main id="main-content">', 1)
if '<a class="skip-link" href="#main-content">Skip to content</a>' not in s:
    s = s.replace('<body>\n', '<body>\n<a class="skip-link" href="#main-content">Skip to content</a>\n', 1)

# Finish Proof with a designed development-status chamber instead of ending
# immediately after the evidence screen.
closing = '''<section class="closing-chamber" aria-label="MASCK ONE development status">
<div class="closing-rule" aria-hidden="true"><span></span><i></i><span></span></div>
<div class="closing-kicker">Current state / engineering development</div>
<div class="closing-wordmark" aria-hidden="true"><span>MASCK</span><span>ONE</span></div>
<div class="closing-bottom">
<div class="closing-statement"><b>Built toward evidence.</b><span>MASCK ONE advances when the physical system earns the claims the digital system proposes.</span></div>
<div class="closing-meta"><span>Product visuals may change.</span><span>No paid pre-orders.</span><span>2026</span></div>
<button class="closing-return" type="button" data-return-architecture><span>Return to Architecture</span><i aria-hidden="true">↗</i></button>
</div>
</section>'''
if 'class="closing-chamber"' not in s:
    anchor = '<div class="page-index">03 / Proof / 02</div><div class="evidence-line">No paid pre-orders. Product visuals may change as physical evidence closes.</div>\n</section>\n</section>\n</main>'
    replacement = '<div class="page-index">03 / Proof / 02</div><div class="evidence-line">No paid pre-orders. Product visuals may change as physical evidence closes.</div>\n</section>\n' + closing + '\n</section>\n</main>'
    if anchor not in s:
        raise RuntimeError('proof closing anchor not found')
    s = s.replace(anchor, replacement, 1)

css = r'''
/* Final website closure v13 */
.skip-link{
  position:fixed;z-index:2200;left:18px;top:14px;
  padding:10px 14px;border-radius:999px;background:#18211c;color:#fbfcf9;
  font:400 8px/1 var(--mono);letter-spacing:.1em;text-transform:uppercase;
  transform:translateY(-180%);transition:transform .2s var(--ease)
}
.skip-link:focus{transform:translateY(0)}

.closing-chamber{
  position:relative;min-height:100svh;padding:clamp(100px,12vh,150px) max(var(--pad),5.2vw) 34px;
  display:flex;flex-direction:column;justify-content:space-between;overflow:hidden;
  background:#f1efe8;color:#18211c;border-top:1px solid rgba(24,33,28,.12);isolation:isolate
}
.closing-chamber::before{
  content:"";position:absolute;z-index:0;right:-17vw;top:-23vw;width:58vw;aspect-ratio:1;border-radius:50%;
  background:radial-gradient(circle,rgba(189,211,215,.50),rgba(189,211,215,.13) 43%,transparent 70%);filter:blur(9px);pointer-events:none
}
.closing-chamber::after{
  content:"03";position:absolute;z-index:0;right:-.025em;bottom:-.12em;
  font:400 clamp(240px,35vw,580px)/.7 var(--display);letter-spacing:-.08em;color:#18211c;opacity:.025;pointer-events:none
}
.closing-rule{position:relative;z-index:2;display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:16px;color:rgba(24,33,28,.30)}
.closing-rule span{height:1px;background:currentColor}.closing-rule i{width:5px;height:5px;border:1px solid currentColor;border-radius:50%}
.closing-kicker{position:relative;z-index:2;margin-top:25px;font:400 7px/1 var(--mono);letter-spacing:.15em;text-transform:uppercase;color:rgba(24,33,28,.48)}
.closing-wordmark{position:relative;z-index:1;align-self:center;width:min(92vw,1260px);margin:auto 0;display:flex;justify-content:center;gap:.12em;
  font:400 clamp(110px,18vw,290px)/.68 var(--display);letter-spacing:-.075em;white-space:nowrap}
.closing-wordmark span:last-child{font-style:italic}
.closing-bottom{position:relative;z-index:2;display:grid;grid-template-columns:minmax(250px,1fr) auto auto;gap:clamp(28px,5vw,76px);align-items:end;border-top:1px solid rgba(24,33,28,.14);padding-top:20px}
.closing-statement{max-width:410px}.closing-statement b{display:block;margin-bottom:8px;font:400 clamp(25px,2.3vw,36px)/.95 var(--display);letter-spacing:-.04em}
.closing-statement span{display:block;max-width:350px;font-size:10.5px;line-height:1.62;color:rgba(24,33,28,.60)}
.closing-meta{display:grid;gap:7px;min-width:150px;font:400 6.5px/1.2 var(--mono);letter-spacing:.11em;text-transform:uppercase;color:rgba(24,33,28,.45)}
.closing-return{appearance:none;border:0;border-bottom:1px solid rgba(24,33,28,.28);background:transparent;padding:8px 0;display:flex;align-items:center;gap:24px;
  font:400 8px/1 var(--mono);letter-spacing:.105em;text-transform:uppercase;cursor:pointer;color:#18211c;transition:border-color .25s var(--ease),gap .25s var(--ease)}
.closing-return i{font-style:normal;font-size:12px;transition:transform .25s var(--ease)}
.closing-return:focus-visible{outline:2px solid #77866f;outline-offset:6px}
@media(hover:hover) and (pointer:fine){.closing-return:hover{gap:32px;border-color:#18211c}.closing-return:hover i{transform:translate(2px,-2px)}}

/* Final interaction consistency. */
button{-webkit-tap-highlight-color:transparent}
.nav button,.closing-return{touch-action:manipulation}
@media(max-width:900px){
  .nav button{min-height:40px}
  .closing-chamber{min-height:100svh;padding:92px 22px max(24px,env(safe-area-inset-bottom))}
  .closing-chamber::before{right:-32vw;top:-8vw;width:100vw}
  .closing-wordmark{width:100%;margin:auto 0;font-size:clamp(75px,24vw,118px);line-height:.72;flex-direction:column;gap:0;align-items:flex-start}
  .closing-wordmark span:last-child{margin-left:18vw}
  .closing-bottom{grid-template-columns:1fr;gap:25px;padding-top:17px}
  .closing-statement b{font-size:clamp(29px,8.7vw,38px)}
  .closing-statement span{font-size:10.5px}
  .closing-meta{grid-template-columns:repeat(3,auto);justify-content:space-between;min-width:0;gap:8px;font-size:5.8px}
  .closing-return{width:100%;justify-content:space-between;min-height:44px}
}
@media(max-width:390px){
  .closing-chamber{padding-left:18px;padding-right:18px}
  .closing-meta{grid-template-columns:1fr;gap:5px}
}
@media(max-width:900px) and (prefers-reduced-motion:reduce){.skip-link,.closing-return,.closing-return i{transition:none!important}}
/* End final website closure v13 */
'''
s = s.replace('\n</style>\n</head>', '\n' + css + '\n</style>\n</head>', 1)

# Wire the closing action through the already-proven view switcher instead of
# inventing a second navigation mechanism.
listener = """\nconst closingReturn=document.querySelector('[data-return-architecture]');\nif(closingReturn)closingReturn.addEventListener('click',()=>switchView('object'));\n"""
needle = "nav.forEach(b=>b.addEventListener('click',()=>switchView(b.dataset.viewTarget)));"
if listener.strip() not in s:
    if needle not in s:
        raise RuntimeError('navigation listener anchor missing')
    s = s.replace(needle, needle + listener, 1)

# Guard against accidental regression of the single approved product mask.
checks = [
    ('closing chamber', s.count('class="closing-chamber"') == 1),
    ('skip link', s.count('class="skip-link"') == 1),
    ('main target', s.count('id="main-content"') == 1),
    ('return listener', s.count("closingReturn.addEventListener('click',()=>switchView('object'))") == 1),
    ('single mask', s.count('mask-journey hero-mask-single') == 1),
    ('approved image', '<img class="hero-mask-art"' in s),
    ('no aperture svg', 'masck-aperture-mask' not in s),
]
for name, ok in checks:
    if not ok:
        raise RuntimeError(f'finalization guard failed: {name}')

INDEX.write_text(s)
print('final website closure v13 complete')
