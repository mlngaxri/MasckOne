from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'website/index.html'
s = INDEX.read_text()

# Remove UI/copy that repeats information already communicated by hierarchy or visuals.
remove_exact = [
    '<div class="nav-status" aria-hidden="true"><i></i><span>In development</span></div>\n',
    '<div class="hero-editorial-kicker"><span>Facial cleansing</span><b>Engineering development</b></div>\n',
    '<div class="handoff-caption"><b>Architecture. Systems. Proof.</b><span>Explore what MASCK ONE is, how it works, and the evidence behind it.</span></div>',
    '<div class="systems-kicker">Contained fluid circuit</div>\n',
    '<div class="systems-kicker">Local motion architecture</div>\n',
    '<div class="systems-readout systems-readout-flow readout-left"><b>FLOW / 01</b><span>Fresh-water + cleanser supply</span></div>\n',
    '<div class="systems-readout systems-readout-flow readout-right"><b>FLOW / 02</b><span>Recovered-fluid return</span></div>\n',
    '<div class="systems-readout systems-readout-motion readout-left"><b>MOTION / A-D</b><span>Four localized zones</span></div>\n',
    '<div class="systems-readout systems-readout-motion readout-right"><b>CONTROL</b><span>Amplitude + timing remain variable</span></div>\n',
    '<div class="page-label">Service and containment</div>\n',
    '<div class="page-label">Integrated evidence</div>\n',
    '<div class="page-index">03 / Proof / 01</div>',
    '<div class="page-index">03 / Proof / 02</div>',
    '<div class="closing-kicker">Current state / engineering development</div>\n',
]
for old in remove_exact:
    s = s.replace(old, '')

# The step number already communicates sequence; the repeated section label does not.
s = s.replace('<div class="systems-step systems-step-flow" aria-hidden="true"><span>02 / Systems</span><b>01</b></div>',
              '<div class="systems-step systems-step-flow" aria-hidden="true"><b>01</b></div>')
s = s.replace('<div class="systems-step systems-step-motion" aria-hidden="true"><span>02 / Systems</span><b>02</b></div>',
              '<div class="systems-step systems-step-motion" aria-hidden="true"><b>02</b></div>')

# Tighten prose. Keep evidence statements; remove explanatory padding.
replacements = {
    'MASCK ONE is a contained facial-cleansing wearable engineered to deliver, move and recover cleansing fluid while your hands stay free.':
        'A contained facial-cleansing wearable that delivers, moves and recovers fluid hands-free.',
    'Supply and return are treated as separate paths through the wearable. Water and cleanser move toward the face while recovered liquid is routed away toward containment.':
        'Fresh water and cleanser move toward the face. Recovered liquid returns to containment through a separate path.',
    'Four localized actuation zones divide motion across the facial interface instead of forcing the entire wearable to behave as one rigid moving structure.':
        'Four local actuation zones distribute motion across the facial interface.',
    'Flow rate, recovery efficiency and leakage remain physical evidence gates.':
        'Flow, recovery and leakage remain unvalidated.',
    'Motion amplitude, force, acoustic perception and comfort remain unvalidated.':
        'Motion, force and comfort remain unvalidated.',
    'The return circuit terminates in a removable cartridge architecture. Recovery and servicing are treated as physical evidence problems, not claims inferred from a render.':
        'Recovered fluid routes to a removable cartridge. Recovery and servicing still require physical validation.',
    'Recovery performance, hygiene and servicing remain evidence-gated.':
        'Recovery, hygiene and servicing remain unvalidated.',
    'The digital assembly resolves the major physical layers and interfaces. The final product only advances when those layers survive fit, flow, airway, motion, recovery, comfort, durability, hygiene and safety evidence.':
        'The digital assembly resolves the major layers and interfaces. Fit, flow, airway, motion, recovery, comfort, durability, hygiene and safety still require physical evidence.',
    'Every layer shown remains subordinate to physical validation.':
        'Every layer still requires physical validation.',
    'MASCK ONE advances when the physical system earns the claims the digital system proposes.':
        'MASCK ONE advances only when physical testing supports the design.',
}
for old, new in replacements.items():
    s = s.replace(old, new)

css = r'''
/* Restraint pass v14 */
.nav-status,.hero-editorial-kicker,.systems-kicker,.systems-readout,.page-label,.page-index,.closing-kicker,.handoff-caption{display:none!important}
.systems-copy h2{margin-top:0!important}
.systems-copy>p{max-width:470px}
.page-copy h2{margin-top:0!important}
.page-copy>p{max-width:455px}
.closing-statement span{max-width:430px}
@media(max-width:900px){
  .systems-copy>p,.page-copy>p{max-width:100%}
}
/* End restraint pass v14 */
'''
if '/* Restraint pass v14 */' not in s:
    s = s.replace('\n</style>\n</head>', css + '\n</style>\n</head>', 1)

# Guardrails: the final site should not regress into redundant status/label copy.
for forbidden in [
    '>In development<',
    'Contained fluid circuit',
    'Local motion architecture',
    'Facial cleansing</span><b>Engineering development',
    'Current state / engineering development',
    'Explore what MASCK ONE is, how it works, and the evidence behind it.',
    '03 / Proof / 01',
    '03 / Proof / 02',
]:
    if forbidden in s:
        raise RuntimeError(f'redundant copy survived restraint pass: {forbidden}')

# Preserve the actual information architecture and approved product treatment.
assert s.count('data-view-target="object"') >= 1
assert s.count('data-view-target="system"') >= 1
assert s.count('data-view-target="proof"') >= 1
assert s.count('mask-journey hero-mask-single') == 1
assert s.count('class="hero-mask-art"') == 1
assert 'No paid pre-orders.' in s
assert '/* Restraint pass v14 */' in s

INDEX.write_text(s)
print('restraint pass v14 complete')
