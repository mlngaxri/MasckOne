# Cost pressure — spending where the user can tell

Read this before adding a tooling action, a tighter tolerance or a part.

## The rule this implements

> Invest where the customer perceives or needs the quality. Reject an elegant
> but excessively expensive architecture when a moulded, stamped, flexural or
> preloaded solution can deliver effectively the same user experience. Do not
> over-engineer internal invisible mechanisms for prestige.

Nothing could evaluate that, because nothing related a mechanism's cost drivers
to whether anyone can perceive it.

## No currency, deliberately

There are no unit costs here and there will not be until a producer quotes the
part. Inventing one would be exactly the fabrication the evidence firewall
exists to prevent — and a wrong cost is more dangerous than no cost, because it
gets carried into decisions and never revisited.

What *can* be established without a quotation is **relative pressure**. A
mechanism needing a side action costs more to tool than one that ejects on the
main pull — on any resin, at any volume, from any producer. Drivers are ranked
by how hard each is to remove:

| Driver | Why it costs |
|---|---|
| `PART_COUNT` | more parts, more assembly, more stack |
| `ASSEMBLY_STEPS` | labour and fixturing |
| `MATERIAL_CLASS` | engineering resin, filled grade, metal insert |
| `TOLERANCE_BURDEN` | tighter process, higher scrap |
| `TOOLING_ACTION` | side action, tool split, unscrewing core |

The two existing screens supply real inputs: tolerance burden from
[`PROCESS_CAPABILITY.md`](PROCESS_CAPABILITY.md), tooling pressure from
[`MOLDABILITY.md`](MOLDABILITY.md).

## Applied: the zero-draft apertures

| | Total | Removable | Verdict |
|---|---|---|---|
| As built (0.00° walls) | 13 | **9** | **AVOIDABLE_COST** |
| Cutters tapered ≥2.10° | 4 | 0 | BALANCED |

The apertures are `SKIN_CONTACT` — the most perceptible class there is — so
spending on them would be justified. But **9 of 13 pressure points are deleted
by tapering the cutters**, which costs a CAD edit. Buying side actions for a
problem a taper solves is precisely the substitution the cost rule rejects.

### Why avoidable cost is checked first

The first version of this module judged only *irreducible* pressure. Both
aperture variants came out `BALANCED`, because all the difference between them
was removable — the model buried the finding it existed to surface.

Avoidable cost now outranks the other verdicts. A mechanism whose pressure a
geometry change would delete is not an architecture to be judged on its merits;
it is an architecture to be changed.

## Both failure modes

Over-investment and under-investment are both findings.

| Example | Perceptibility | Verdict |
|---|---|---|
| Sealed internal preload with a side action and a tight stack | `INTERNAL_INVISIBLE` | `OVER_ENGINEERED` |
| Hand-operated control that is a cap on a commodity switch | `HAND_OPERATED` | `UNDER_INVESTED` |

The *same* drivers are judged differently by perceptibility — that is the whole
mechanism. Tooling actions and tight tolerances on a hand-operated control are
balanced; identical spending on something sealed inside is prestige engineering.

## What this is not

`RELATIVE_COST_PRESSURE_NOT_QUOTED_OR_MODELLED_UNIT_COST`.

Ordinal, not quantitative. It ranks mechanisms against each other and against
their own perceptibility. It cannot tell you what anything costs, what tooling
will be quoted at, what volume changes, or whether a supplier will agree. Those
need a producer.
