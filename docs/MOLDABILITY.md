# Moldability — draft on the released shell

Read this before changing aperture geometry, the shell part split, or the
exterior finish specification.

## The finding

Every protected aperture in the rigid shell has **zero draft**.

| Face | Feature | Draft | Area |
|---|---|---|---|
| EXTRUSION ×2 | eye apertures | **0.00°** | 217.3 mm² each |
| EXTRUSION ×1 | mouth aperture | **0.00°** | 259.8 mm² |
| CYLINDER ×2 | nostril apertures | **0.00°** | 70.6 mm² each |
| BSPLINE ×4 | lofted shell surfaces | 7.1–12.8° | — |
| PLANE ×3 | top/bottom | 90° | — |

The problem is entirely local to the apertures. The lofted body is drafted
comfortably. The apertures are cut by cutters extruded straight along the pull
direction (`_ellipse_cutter`, `_circle_cutter` in `model.py`), so their walls
sit exactly parallel to it.

**835.5 mm², 1.11 % of surface area, at 0°.** A 0° wall in a 1.8 mm section drags
the full depth of the draw on every shot.

## Why it matters more than 1.11 % suggests

These are not hidden internal walls. They are the eye, nostril and mouth edges —
the most visible surfaces on the product, the ones the wearer looks through, and
the ones the specified fine satin finish exists for.

Draft and texture are coupled. A polished face releases at around 0.5°; texture
adds roughly **1° per 0.025 mm of depth**. At the specified fine satin
(~0.040 mm), the requirement is **2.10°**. Zero-draft textured walls do not
release cleanly — they scuff, and scuffing on an aperture edge is exactly the
defect the CMF direction rules out (`no obvious gate/ejector scars in visual
areas`).

## What closes it

Three options, in increasing cost:

1. **Draft the aperture cutters.** Replace the straight extrusions with tapered
   ones at ≥2.10°. On a 1.8 mm wall that changes the aperture dimension by
   ~0.066 mm between faces — well inside the authority's aperture tolerances,
   and it costs nothing but the CAD edit. **This is almost certainly the answer.**
2. **Split the tool** so the apertures form on a different parting line. Adds
   tooling cost and a witness line across a visible surface.
3. **Side actions** for the apertures. Most expensive, and puts a parting line
   exactly where the product must look continuous.

Option 1 needs the aperture geometry to declare which face carries the nominal
dimension — the authority states `visual_aperture_wh_mm` without saying whether
that is the wearer-side or exterior face. On a drafted aperture those differ.

## Status

`GEOMETRIC_DRAFT_SCREEN_NOT_MOULD_FLOW_OR_EJECTION_SIMULATION`.

This measures the angle between each face and a declared pull direction. It says
nothing about fill, packing, warp, shrink, ejector layout, gate position, weld
lines, or whether a given texture releases on a given resin. Those need a tool
maker and a moulding simulation.

The pull direction (+Z) is **declared**, not inferred — the shell lofts along +Z
and every cutter extrudes along +Z. If the part split changes, that declaration
must change with it.

`rigid_shell` is `CAD_BASELINE` development geometry, so this does not fail the
build. `tests/test_moldability.py` ratchets it: five undrafted faces and 1.11 %
of area was the measured state, and it may only improve.
