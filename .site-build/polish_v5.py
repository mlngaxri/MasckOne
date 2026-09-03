from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/'website/index.html'
s=INDEX.read_text()

css=r'''
/* Micro finish polish v5 */
body:before{border-color:rgba(24,33,28,.10)}
.header{height:52px;padding-left:18px;padding-right:8px}
.brand{letter-spacing:.21em}
.nav{gap:1px;padding:2px}
.nav button{padding:8px 14px;color:rgba(24,33,28,.70)}
.nav button.active{color:var(--white);transform:none}
.nav button:focus-visible{outline:2px solid #75866c;outline-offset:3px}
@media(hover:hover) and (pointer:fine){.nav button:not(.active):hover{background:rgba(24,33,28,.055);color:var(--ink);transform:translateY(-1px)}}

.hero{background:radial-gradient(circle at 74% 34%,rgba(255,255,255,.48),transparent 26%),linear-gradient(145deg,#f4efe7 0%,#edf1ed 51%,#dce8eb 100%)}
.hero-copy p{border-top-color:rgba(24,33,28,.18)}
.hero-clouds.hero-sky-orb{box-shadow:inset 0 0 55px rgba(255,255,255,.16)}
.hero-mask-product{backface-visibility:hidden;-webkit-backface-visibility:hidden}
.band{backface-visibility:hidden;-webkit-backface-visibility:hidden}
.band-track{transform:translateZ(0)}
.hero-bottom{letter-spacing:.105em}

.handoff-caption b{max-width:430px;text-wrap:balance}
.handoff-caption span{max-width:405px}
.mask-orbit-node span{font-kerning:normal}

.page{border-top-color:rgba(24,33,28,.11)}
.page-copy{max-width:520px}
.page-copy>p{max-width:420px}
.page-label{letter-spacing:.14em}
.detail-card b{letter-spacing:.125em}
.detail-card{color:color-mix(in srgb,currentColor 76%,transparent)}
.visual-stage img.primary{max-width:92%;max-height:92%}
.page.dark .visual-stage img.primary,.page.clay .visual-stage img.primary{max-width:94%;max-height:94%}
.section-tag{letter-spacing:.125em}
.page-index{letter-spacing:.105em}
.evidence-line{letter-spacing:.045em}

@media(max-width:900px){
  body:before{border-color:rgba(24,33,28,.085)}
  .header{height:49px;padding-left:13px;padding-right:6px}
  .nav button{padding:8px 9px}
  .hero-copy{top:12.2svh}
  .hero h1{letter-spacing:-.052em}
  .hero-clouds.hero-sky-orb{top:29svh;width:62vw}
  .hero-mask-wrap.hero-subject{top:35.5svh;width:67vw}
  .band{height:clamp(55px,14.6vw,63px)}
  .band.masck{top:51.5%}.band.one{top:67%}
  .handoff-caption{line-height:1.62}
  .page{padding-top:82px}
  .visual-stage img.primary{max-width:96%;max-height:96%}
  .detail-card{line-height:1.58}
}

@media(max-width:390px){
  .header{height:47px}
  .nav button{padding-inline:7px}
  .hero-copy{top:11.7svh}
  .hero-clouds.hero-sky-orb{top:31.5svh;width:65vw}
  .hero-mask-wrap.hero-subject{top:38.5svh;width:69vw}
}
'''
if '/* Micro finish polish v5 */' not in s:
    s=s.replace('\n</style>\n</head>',css+'\n</style>\n</head>',1)

# Add aria-current to current nav item and maintain it during view changes.
s=s.replace('data-view-target="object" aria-pressed="true">Architecture</button>','data-view-target="object" aria-pressed="true" aria-current="page">Architecture</button>',1)
old="b.setAttribute('aria-pressed',String(isActive))}"
new="b.setAttribute('aria-pressed',String(isActive));if(isActive)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current')}"
if old in s and new not in s:
    s=s.replace(old,new,1)

# Lazy decode imagery in hidden Systems/Proof views; keep hero and journey eager.
def lazy_tag(m):
    tag=m.group(0)
    if 'hero-mask-product' in tag or 'mask-journey' in tag:
        return tag
    if 'loading=' not in tag:
        tag=tag[:-2]+' loading="lazy" decoding="async" />' if tag.endswith('/>') else tag
    return tag

# Restrict to content after Systems begins so hero/handoff stay untouched.
marker='<section class="view" data-view="system"'
if marker in s:
    a,b=s.split(marker,1)
    b=re.sub(r'<img\b[^>]*?/>',lazy_tag,b)
    s=a+marker+b

if '/* Micro finish polish v5 */' not in s: raise RuntimeError('v5 css missing')
if 'aria-current="page">Architecture' not in s: raise RuntimeError('nav semantics missing')
if 'loading="lazy" decoding="async"' not in s: raise RuntimeError('lazy imagery missing')
INDEX.write_text(s)
print('micro finish polish v5 complete')