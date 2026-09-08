# Cell 11 supported-liner decision and closure boundary

## Oblique service corridor and blind key follow-up

The key now uses a lateral blind pocket with actual closure floor and roof lands.
The key opening cuts both collar and underlying liner skin; this avoids a detached
skin island. Tests require those lands and the seal reference to be actual material.
The connected geometric cavity remains 35.38573221526349 mL. Neither the pocket
nor its dry reservation is counted as fluid space. This is geometry, not leakage
validation. Process capability for the thin liner remains unresolved.

A continuous oblique withdrawal corridor is now constructed for translation
(0,+30,-45) mm, with the device removed and unpowered. Three convex polyhedral
enclosures cover the entire body and closure: exact B-rep difference contains no
remaining solids. Each enclosure's translation image is its exact convex hull
with the translated endpoint, covering the whole closed interval, not sampled
poses. The enclosures include conservative padding and remain reference geometry.
They are never capacity or product material.

The complete sweeps have zero intersection against released shell, nasal,
four actuator packages, water and battery packages, and the unchanged current
Cell 6 frame candidate. The frame is consumed byte-for-byte from PR #117 head
`34273de3bd86294080e51873c212e988b4a966f4`, source blob
`0ea2ada736825fe1a0e06491d16690ae98cfccde`; its ownership and unresolved joins
are preserved. A (0,+20,-45) mm trial is rejected by a small frame collision;
the chosen +30 mm transverse travel clears it without modifying the frame.

This establishes a shell/package/frame corridor, **not complete installed service**.
At an exact (0,+0.6,-0.9) mm witness, unreleased bolts intersect moving cartridge
material by approximately 0.633644 mm3 each and the fixed key by 0.4 mm3. Key/bolt
capture and access, wet-route disconnection/passive-backflow sequence, device-side
interface attachment, and integration with the exterior owner's shell remain open.
The review explicitly keeps `continuous_installed_device_path_proven=false`.

The prior head `96397f9e1142224979bfc43717ccf325d07fc21f` completed exact engineering
CI run `34162149979`: 778 passed, CAD smoke and source-bound artifacts succeeded.
That green belongs to that head. The blind-key/service follow-up requires its own
focused checks, exact-head CAD review and full engineering CI before promotion.

Released main: `b3be4c2483f45b2b8dfff6f0c3d9810c2b8511dc`.
This advances the existing Cell 11 owner, PR #115, from
`4da053e57534c98617b9e8abfae7a35436a3718c`. It does not establish a second cartridge
authority. The exact PR #129 mechanical-test prerequisite remains candidate history.

| Constraint | Classification and disposition |
|---|---|
| World coordinates | Frozen datum; unchanged |
| 74 x 36 x 20 mm package at (0,-80,8) | Authority engineering baseline; unchanged |
| Mouth/eye/nostril exclusions | Authority-derived conservative 2.5D hard regions; unchanged |
| 35 mL retained capacity | Validation-gated authority threshold; geometric accounting is separate |
| Waste acquisition, pump, passive barrier, cartridge order | Released source graph; preserved with exact route digest and source blobs |
| Inlet (-41,-82,14) to body (-37,-82,14) | Released route handoff and local interface; unchanged |
| Historical 1.2 mm walls / deep plug | Provisional seed; replaced |
| Liner/floor/lid 0.15 mm; local collar 0.8 x 0.6 mm | DOE only; material and forming/bond process capability unknown |
| One degree draw | Manufacturing engineering baseline, applied to the drafted liner profiles |
| Device dock frame attachment and access | Unresolved; no imaginary frame counterpart added |
| Seal fits, media, rheology, pump performance, human use | Unknown or physical validation required |

The historical cavity was 27.4016290784 mL. Its 1.2 mm in-plane topology cannot
reach 35 mL even with zero floor/lid. The new architecture uses a thin formed
liner, shallow separately reinforced closure, a continuous closure bond-land
reference, a reinforced inlet socket, a deducted vent/media reservation, dry
retention islands, an asymmetric key and bilateral positive sliding bolts.
The full package and protected geometry are not enlarged or moved.

The new nominal principal free cavity is **35.3857322153 mL**, margin
**+0.3857322153 mL**. Body, closure and cavity are individually valid connected
solids. Actual dry bolt sockets are excluded from the cavity; an initial
disconnected socket void was detected and removed from fluid accounting.
Body and closure measure zero intersection with the released shell and all five
protected prisms. All material/reference identities are explicit in the manifest.

Search comparisons used thick tray, shallow closure and rear-passage profiles,
followed by a drafted supported-liner DOE. A 0.6 mm wall/floor and 0.25 mm film
ceiling in the chosen shell-conforming pocket is 33.5833004 mL before interfaces;
the rear-passage variant has only 31.6504624 mL. Neither can close the requirement.
The chosen shell-conforming pocket has a 37.5673699 mL no-wall ceiling. This is a
**construction-specific conservative pocket**, not a proof of maximum space in
every possible cartridge or exterior architecture. The full package minus the
protected mouth remains approximately 40.21067 mL before material.

Measured nested side-surface separation is 0.141429609 mm. The 0.15 mm floor/lid
and film seeds do not establish process minimum, strength, creep or durability.
Independent +0.025 mm wall/floor/lid perturbations leave 35.28543, 35.34374 and
35.33962 mL respectively. These are DOE sensitivities, not a production tolerance
stack. The modest nominal margin does not justify manufacturing release.

Both local bolt retraction sweeps are exact continuous axial-cylinder unions,
with zero closure, guide and released-shell intersection. Retracted clearance
to the closure is approximately 0.910743 mm. Bolts block attempted cartridge
translation when engaged, and the asymmetric key obstructs reversed orientation.
Device-frame attachment, bolt capture/access and wet disconnect remain unresolved.

The current inferior and posterior straight service paths are rejected by exact
material collision witnesses after only 1 mm: respectively 126.1537223 and
59.6049606 mm3. Their continuous AABB envelopes are conservatively screened, but
are explicitly not exact material swept-volume measurements. A clear sampled
pose is never reported as a complete service proof. A tentative advance/tilt
route needs a robust whole-material continuous sweep and complete interface
release before it can replace this BLOCKED result.

Five gravity orientations use exact B-rep/half-space intersections under an
explicit hypothetical open-port condition. No wetting, valves, foam, contact
angle, pump curve or mixed-phase CFD is invented. The results are not retained
capacity, leakage or residual-liquid evidence.

Reproduce the standalone review using
`python -m masck_one.waste_cartridge_analysis --output generated/cartridge-review`.
It exports material/reference STEP, three source-generated SVG views, capacity
sensitivity, wall separation, local continuous bolt sweeps, service obstructions,
orientation fill geometry and STEP read-back measurements. The CI review artifact
binds its exact head/tree/base and every output hash. Normal CAD smoke also emits
the candidate parts and manifest separately from development assembly material.

**HOLD for digital MVP:** installed-device service, complete dock/actuation and
wet-interface release, forming/bond processes, tolerance fits and removed-state
port closure remain open. Physical retained capacity, leakage, recovery, hygiene,
durability and human-use evidence remain required. No production or physical MVP
claim is made. Independent exact-head review is required before any promotion.
