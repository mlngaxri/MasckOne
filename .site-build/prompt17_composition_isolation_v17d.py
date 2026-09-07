from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "website" / "index.html"
MARKER = "/* Prompt 17 composition isolation v17d */"
FINAL_MARKER = "/* Product inspection final v17c */"

s = INDEX.read_text(encoding="utf-8")
if MARKER in s:
    print("Prompt 17 composition isolation v17d already applied")
    raise SystemExit(0)
if FINAL_MARKER not in s or s.count('data-product-orbit17') != 1:
    raise RuntimeError("final Prompt 17 chapter missing or duplicated")

css = r'''
/* Prompt 17 composition isolation v17d */
body.orbit17-inspection-active .mask-journey,
body.orbit17-inspection-active .mask-orbit-overlay,
body.orbit17-inspection-active .handoff-halo{
  opacity:0!important;
  visibility:hidden!important;
  pointer-events:none!important;
}
'''

js = r'''
<script>
(()=>{
const section=document.querySelector('[data-product-orbit17]');
const architecture=section?.closest('[data-view="object"]');
if(!section||!architecture)return;
let queued=false;
function sync(){
  queued=false;
  const r=section.getBoundingClientRect();
  const active=architecture.classList.contains('active')&&r.top<innerHeight*.92&&r.bottom>innerHeight*.08;
  document.body.classList.toggle('orbit17-inspection-active',active);
}
function request(){if(queued)return;queued=true;requestAnimationFrame(sync)}
addEventListener('scroll',request,{passive:true});
addEventListener('resize',request,{passive:true});
document.querySelectorAll('[data-view-target]').forEach(button=>button.addEventListener('click',()=>requestAnimationFrame(sync)));
sync();
})();
</script>
'''

if s.count("\n</style>\n</head>") != 1:
    raise RuntimeError("style insertion point moved")
if s.count("\n</body>\n</html>") != 1:
    raise RuntimeError("script insertion point moved")
s = s.replace("\n</style>\n</head>", css + "\n</style>\n</head>", 1)
s = s.replace("\n</body>\n</html>", js + "\n</body>\n</html>", 1)
INDEX.write_text(s, encoding="utf-8")
print("Prompt 17 composition isolation v17d applied")
