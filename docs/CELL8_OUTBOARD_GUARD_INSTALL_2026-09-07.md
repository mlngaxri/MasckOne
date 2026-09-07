# Complete outboard adjustment-guard installation

Current main is `b3be4c2483f45b2b8dfff6f0c3d9810c2b8511dc`.
The unchanged yoke geometry is consumed from PR #123 head
`25686766238b66ecf900009042d721c08e042592`, exact source blob
`6d35c96bc65bb1e0e877deadc65481bf44954b4e`.
Cell 3 #92 live head is `88a88bed01fd3b3acfb38ff5f6f3ae3d5bbf54fe`;
its hazard/load-path geometry blobs remain unchanged. Closed #71 is a pinned
historical quick-release donor, not a new release approval.

The former inboard installation crossed each installed yoke by approximately
39.840676 mm3. It also crossed the corresponding protected-eye prism by
137.572140 mm3 and the scalp approach reservation by 665.156250 mm3.
Those complete-path checks were missing although the seated guards were clear.

Both U-shrouds are open in X. Start the right guard 22 mm outboard and translate
-22 mm to its unchanged seat. Mirror this motion on the left. The complete sweep
is the union of exact X prisms for **all three material boxes**, analytically
equal to the full closed-interval translation image. There is no sampled-pose
approximation, shape healing, new clearance tolerance, or material redesign.

The new bilateral sweeps have zero forbidden volume against installed yokes,
all bound mechanism hazards, root/scalp reservations, protected anatomy,
released shell/nasal/actuator/water/waste/battery geometry, other guards and
quick-release access. Minimum yoke distance is 2.462214450449026 mm. Each sweep
has volume 2124.375 mm3. Right bounds are X [76.5,109.5], Y [-1.5,29],
Z [-37.5,-25.75] mm; left bounds are mirrored. The starting guard is fully
outside the seated guard with 11 mm axial separation. The motion is reversible.

Focused guard/yoke tests: 25 passed locally. The hostile regression restores
the old motion while leaving final geometry unchanged and requires rejection.
An exact-source review job exports guards, sweeps and source-bound yokes,
validates STEP solids and bidirectional material equality, and records hashes.
Full engineering CI and CAD smoke remain required separately.

This closes the guard/yoke **installation interference**, not factory assembly.
Positive guard/frame mating attachment and its fastener/tool access remain
unrealized. The unchanged yoke donor is not a second redesigned yoke owner.
Guards and yokes remain standalone material candidates; sweeps remain references.
No material, load, hair safety, comfort, release-force/time or durability evidence
is promoted. Whole-head removal and complete retention load path remain open.
