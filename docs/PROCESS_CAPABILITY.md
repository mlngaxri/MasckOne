# Process capability — can the tolerance actually be held?

Read this before tightening any tolerance, and before choosing a part split that
puts a visible seam somewhere convenient.

## The gap this fills

`mechanism_tolerance.py` does worst-case interval arithmetic on dimension chains
and says so plainly: it *"does not claim manufacturing capability"*. Nothing else
did either. So the repository could state a tolerance, stack it correctly, and
never ask the question that decides whether any of it means anything:

> A 0.02 mm CAD clearance is meaningless if the moulding process cannot hold the
> full stack.

`src/masck_one/process_capability.py` asks it.

## Two structural facts

**Achievable tolerance follows the length of the dimension chain, not the size
of the part.** A 20 mm feature referenced to a local mating datum is held far
tighter than the same feature referenced across a 200 mm outline — same tool,
same shot, same material. Shortening the chain is usually cheaper than
tightening the process.

**Worst-case is the only defensible method here.** Statistical (RSS) stacking
assumes known, centred, capable processes — it needs Cp/Cpk from a qualified
supplier running a qualified tool. No such data exists for this programme. RSS
is computed for reference and `rss_is_usable` is hard-wired to `False`.

Because worst-case adds magnitudes, N equal contributors each get `budget/N`.
**Removing one contributor from a three-part chain buys 1.5× — more than most
process tightening will.**

## Applied: the visible seam

`geometry.visible_seam` requires a 0.40 mm gap held to ±0.15 mm. Whether that is
holdable depends entirely on how the seam is located, which is an
industrial-design and part-split decision, not a process decision.

| Control strategy | Contributors | Chain | Required each | Moulding holds | Verdict |
|---|---|---|---|---|---|
| Butt joint, referenced to global outline | 3 | 200 mm | ±0.050 mm | ±0.167–0.306 mm | **INFEASIBLE, 6.13×** |
| Self-locating local mating datum | 2 | 20 mm | ±0.075 mm | ±0.033–0.064 mm | **FEASIBLE, 0.85×** |

Referenced to the part outline, the seam gap accumulates each shell's edge
position relative to the common locating frame, plus the frame itself — three
contributors over the full 200 mm outline. It misses by roughly **six times**.
No amount of process control closes that.

Locating the seam **to itself** — the two shells mating via a shiplap or tongue
right at the seam — does two things at once: it removes the frame term, and it
collapses the chain from the 200 mm outline to the ~20 mm local feature. That
moves the requirement from ±0.050 mm to ±0.075 mm and the capability from
±0.31 mm to ±0.064 mm. It is then held **even at the pessimistic end of the
band**.

`geometry.visible_seam.control_strategy` now declares this explicitly, and
`authority.py` raises `VISIBLE_SEAM_TOLERANCE_NOT_MANUFACTURABLE` during
semantic validation if the declared strategy cannot hold the declared tolerance.
The gate catches the defect from either side: switching to the butt joint fails,
and so does tightening `tolerance_mm` past what the strategy supports.

### Why this is an ID decision, not a tolerance decision

The brief asks that a mechanism causing an ugly exterior be answered by
rethinking the part split rather than hiding it. This is the same thing in
reverse: an exterior requirement that cannot be manufactured is answered by
changing where and how the parts meet, not by writing a tighter number on a
drawing nobody can hold to.

A self-locating seam also changes what the user feels. A butt joint that varies
by ±0.3 mm reads as a gap that opens and closes along its length; a shiplap that
locates itself reads as one continuous controlled line — and it cannot rub,
which is what produces squeak.

## Using it elsewhere

`assess_stack()` is general. Any clearance with a tolerance budget, a
contributor count and a chain length can be screened:

```python
assess_stack(
    "CARTRIDGE_KEY_ENGAGEMENT",
    process=ProcessClass.INJECTION_MOULDED_FILLED,
    chain_length_mm=40.0,
    contributor_count=4,
    total_budget_mm=0.30,
)
```

The cartridge service corridor, the primary-control guide bushings and the
retention adjustment all have exactly this shape, and all three sit in other
lanes. Screening them belongs to those lanes; the engine is here for them.

## What this is not

`PLANNING_VALUES_NOT_SUPPLIER_OR_MEASURED_PROCESS_CAPABILITY`.

The capability bands are planning values in the spirit of ISO 20457 / DIN 16901
general tolerance guidance for moulded plastics, quoted as ranges rather than
constants. They are not a quotation, not a supplier commitment, not measured
capability, and not specific to any resin, tool or press.

A real tolerance budget is agreed with the producer who will cut the tool, from
their measured capability on their equipment. This module tells you when a
number is obviously unholdable — which is worth knowing before a tool is cut,
not after.
