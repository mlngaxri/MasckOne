from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'website/index.html'
s = INDEX.read_text()

css = r'''
/* Stage 4 rendered visual QA v16 */
/* The current approved alpha render contains chromatic corruption in its lower
   region. Neutralise colour only; do not redraw, crop or alter its silhouette. */
.hero-mask-art{
  filter:grayscale(.76) sepia(.10) saturate(.48) contrast(.96) brightness(1.035)!important;
}

/* The Architecture object is the focal point. Supporting orbit words stay
   legible but deliberately recede instead of all competing at full weight. */
.mask-orbit-node span{
  font-size:clamp(34px,4.35vw,64px)!important;
  opacity:.20;
  text-shadow:none!important;
}
.mask-orbit-node:nth-child(1) span{opacity:.90}
.mask-orbit-node:nth-child(2) span,.mask-orbit-node:nth-child(3) span{opacity:.18}
.handoff-halo{opacity:.12!important}

/* Remove decorative words/numerals that repeat information already provided
   by headline, navigation and composition. */
.systems-word{display:none!important}
.page[data-page-no]::before{display:none!important}

/* Temporary integration treatment for the existing raster engineering images.
   The final transparent assets can replace these one-for-one through their
   data-asset-slot hooks without changing layout or motion. */
.systems-flow-visual .systems-product-frame img{
  mix-blend-mode:multiply;
  filter:grayscale(.52) sepia(.08) saturate(.62) contrast(1.12) brightness(1.04)!important;
  -webkit-mask-image:radial-gradient(ellipse 72% 68% at 50% 50%,#000 42%,rgba(0,0,0,.96) 60%,rgba(0,0,0,.38) 78%,transparent 96%);
  mask-image:radial-gradient(ellipse 72% 68% at 50% 50%,#000 42%,rgba(0,0,0,.96) 60%,rgba(0,0,0,.38) 78%,transparent 96%);
}
.systems-motion-visual .systems-product-frame img{
  mix-blend-mode:screen;
  filter:grayscale(.50) sepia(.06) saturate(.62) contrast(1.05) brightness(.94)!important;
  -webkit-mask-image:radial-gradient(ellipse 74% 70% at 50% 50%,#000 44%,rgba(0,0,0,.96) 62%,rgba(0,0,0,.32) 80%,transparent 97%);
  mask-image:radial-gradient(ellipse 74% 70% at 50% 50%,#000 44%,rgba(0,0,0,.96) 62%,rgba(0,0,0,.32) 80%,transparent 97%);
}
.page.dark .visual-stage .primary{
  -webkit-mask-image:radial-gradient(ellipse 76% 72% at 50% 50%,#000 48%,rgba(0,0,0,.96) 64%,rgba(0,0,0,.30) 82%,transparent 98%);
  mask-image:radial-gradient(ellipse 76% 72% at 50% 50%,#000 48%,rgba(0,0,0,.96) 64%,rgba(0,0,0,.30) 82%,transparent 98%);
}

/* Make the technical visual itself quieter: no ornamental frame around a
   rectangular raster that will disappear once the transparent asset lands. */
.systems-product-frame:before{opacity:.28!important;border-radius:50%!important}
.systems-core-axis{opacity:.55}

@media(max-width:900px){
  .hero-mask-art{filter:grayscale(.72) sepia(.08) saturate(.52) contrast(.97) brightness(1.03)!important}
  .mask-orbit-node span{font-size:clamp(27px,7.2vw,38px)!important}
  .systems-flow-visual .systems-product-frame img,.systems-motion-visual .systems-product-frame img,.page.dark .visual-stage .primary{
    mix-blend-mode:normal;
  }
}
/* End Stage 4 rendered visual QA v16 */
'''

if '/* Stage 4 rendered visual QA v16 */' not in s:
    s = s.replace('\n</style>\n</head>', css + '\n</style>\n</head>', 1)

assert '/* Stage 4 rendered visual QA v16 */' in s
assert '.systems-word{display:none!important}' in s
assert '.page[data-page-no]::before{display:none!important}' in s
assert 'mix-blend-mode:multiply' in s
assert 'mix-blend-mode:screen' in s
assert s.count('mask-journey hero-mask-single') == 1
assert s.count('class="hero-mask-art"') == 1

INDEX.write_text(s)
print('stage 4 rendered visual QA v16 complete')
