# Masck One facial-region and coverage-analysis mesh

## Purpose

Iteration 9 establishes the topology and accounting system that later Masck One cleansing geometry and physical efficacy data will use to answer a precise question: **which intended facial target areas are reached, which safety-excluded areas are intentionally not targeted, and where do unexplained uncovered holes remain?**

The system is deliberately separated from any claim that the present device cleans effectively. A coverage-analysis mesh is a measurement framework; it is not cleansing-efficacy evidence by itself.

## Authority versus CAD-closure definitions

The machine authority currently freezes the following coverage requirements:

- aggregate cleansing coverage: **at least 90%** of the applicable target area;
- T-zone coverage: **at least 90%** of the applicable T-zone target area;
- largest unexplained uncovered hole: **no more than 100 mm²**.

These values are consumed directly from `config/masck_one_authority.yaml`.

The authority does **not** presently freeze an exact anatomical polygon for the T-zone. Iteration 9 therefore introduces a deterministic development-only T-zone boundary so algorithms, IDs, area accounting and future outlet/manifold work can proceed without pretending that a CAD convenience definition is anatomical truth.

Its status is:

`CAD_CLOSURE_BASELINE_DERIVED_FROM_AUTHORITY_GEOMETRY_NOT_ANATOMICAL_VALIDATION`

A later registered/anatomically approved facial dataset may replace/refine this segmentation through controlled change review.

## Current development T-zone derivation

No new arbitrary facial landmark coordinates are introduced. The current T-zone is derived from geometry already controlled elsewhere in the project.

### Nose / central stem

The central stem half-width is the maximum lateral outer extent of the existing left/right nostril protected envelopes:

`abs(nostril center X) + protected-envelope half-width`

This deliberately keeps the T-zone concept coupled to the nose/airway architecture rather than inventing an unrelated central stripe.

The stem lower boundary is the superior edge of the protected mouth envelope:

`mouth center Y + protected mouth envelope height / 2`

With the current authority values this is **Y = −24.5 mm**.

The stem upper boundary is the inferior-to-forehead transition derived from the eye line plus half the current eye aperture height:

`eye center Y + eye aperture height / 2 = +50.0 mm`

Therefore the current central development stem extends continuously from the upper-lip/philtrum region at the mouth safety boundary through the nose and bridge to **Y = +50.0 mm**.

### Forehead crossbar

The forehead crossbar begins at the exact same Y coordinate, **+50.0 mm**, so there is no artificial vertical gap between the central stem and forehead portion.

Its half-width is derived from the lateral eye-center location plus half the eye aperture width:

`31.5 mm + 46/2 mm = 54.5 mm`

Again, this is an engineering baseline for deterministic topology—not a statement that every person's biological T-zone ends at this line.

## Nose and upper-lip coverage continuity

A specific regression condition requires a positive active target area between the nose and the superior mouth protected boundary.

The code exposes `philtrum_target_area_mm2` and refuses to construct the development coverage mesh if this area is zero.

This prevents a future CAD edit from accidentally turning the entire area between the nose and upper lip into an omission merely because nostril and mouth safety exclusions exist nearby.

The nostril/airway protected areas themselves remain excluded targets. The surrounding nose, sidewall, bridge and philtrum-development region remain targetable.

## Triangle-level partition

Every triangle in the neutral facial surface receives exactly one deterministic coverage record containing:

- stable triangle index;
- three source vertex indices;
- 3D centroid;
- 3D triangle area in mm²;
- region ID;
- optional protected-zone ID;
- active-target flag;
- T-zone-target flag.

The current region vocabulary includes:

- `ACTIVE_FACE_OTHER`
- `T_ZONE_FOREHEAD`
- `T_ZONE_NOSE_PHILTRUM`
- one protected region for each eye, mouth and nostril/airway target.

The sum of active-target area and protected area must equal total source-surface area within numerical tolerance.

## Conservative protected-zone classification

The current facial surface is a development surface, while the protected zones are conservative planar safety exclusions whose anatomical depth remains unresolved.

For segmentation, a triangle is classified as protected if **any of its vertices or its centroid** enters a protected XY envelope.

This is intentionally more conservative than classifying only the centroid. It reduces the chance that a coarse triangle crossing an exclusion boundary is accidentally counted as a cleansing target.

This still does not close dynamic 3D eye, mouth or airway safety. Those checks remain separately blocked until evidence-eligible registered dynamic anatomy exists.

## Surface area

Triangle area is calculated in full 3D using the cross product of triangle edge vectors.

On the current planar development surface, this reduces to ordinary planar area. When a registered 3D facial surface is later approved, the same accounting method can measure true mesh surface area without changing the coverage-data model.

## Coverage evaluation input

The evaluator accepts a set of **covered active-target triangle IDs**.

Iteration 9 does not invent those covered IDs. Later subsystems may derive them from, for example:

- validated fluid-delivery footprint modelling;
- actuator/contact-envelope calculations;
- dyed-fluid or fluorescent coverage tests;
- artificial-skin cleansing experiments;
- spatial efficacy measurements mapped back to the registered surface.

Protected triangles cannot be submitted as covered targets. Unknown triangle IDs are rejected.

## Aggregate coverage

Aggregate coverage is area-weighted:

`100 × covered active-target area / total active-target area`

It is not a triangle-count percentage, so a dense region of small triangles cannot bias the result.

## T-zone coverage

T-zone coverage is also area-weighted:

`100 × covered T-zone target area / total T-zone target area`

Protected eye/mouth/nostril areas are not counted in either numerator or target denominator.

## Unexplained-hole metric

The 100 mm² hole requirement is implemented as the largest **edge-connected component** of uncovered active-target triangles.

Two triangles are adjacent only when they share a full mesh edge. Vertex-only contact does not merge two holes.

The algorithm:

1. builds target-triangle edge adjacency;
2. subtracts the covered-target set;
3. finds each connected uncovered component;
4. sums its triangle areas;
5. reports the largest component area.

This gives a deterministic spatial-hole measure rather than allowing high overall coverage to hide one large missed patch.

## Evidence-aware result states

A numeric result is deliberately separate from product validation.

Examples:

- a synthetic test fixture that marks every active target triangle as covered produces 100% aggregate, 100% T-zone and 0 mm² largest hole;
- on the current planar synthetic surface, the result is still labelled `NUMERIC_SCREEN_PASS_NOT_PRODUCT_VALIDATION`;
- numeric failure is labelled `NUMERIC_GATE_FAIL`;
- even on a future evidence-eligible anatomical surface, numeric success still requires the appropriate physical validation protocol before claims are accepted.

This prevents a software-perfect mask from being confused with a physically effective cleanser.

## Determinism and traceability

The segmentation manifest includes:

- source surface ID and mesh hash;
- T-zone development definition;
- authority thresholds;
- per-triangle region/target classification;
- areas;
- evidence state.

It is SHA-256 signed through `segmentation_sha256`.

A coverage evaluation also receives its own SHA-256 over the segmentation identity, covered-target set and evidence metadata. Equivalent covered sets yield the same evaluation hash regardless of input ordering.

## Current limitations

Iteration 9 does not establish:

- biological/anatomical T-zone boundaries across the target population;
- a final 3D face surface;
- final cleansing-fluid footprint;
- final actuator-contact footprint;
- efficacy of cleanser removal;
- physical wetting uniformity;
- sunscreen/makeup/sebum removal performance;
- human-use coverage;
- population probability of coverage.

Those remain later engineering and validation tasks.

## Change-control rule

Any future change to region boundaries, protected-zone treatment, area denominator rules, connectivity definition, threshold interpretation, or evidence-status behavior must be treated as a coverage-system change and regression-tested. Threshold values themselves remain authority-controlled and must not be copied into independent hard-coded product logic.
