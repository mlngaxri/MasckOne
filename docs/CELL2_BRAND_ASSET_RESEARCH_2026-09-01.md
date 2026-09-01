# Cell 2 brand asset research, 2026-09-01

## Scope

Fresh public-source review for small-scale brand assets and launch-source geometry. This is design research, not trademark clearance or evidence promotion.

## Sources and principles

- Apple Developer, Design Resources and Icon Composer, accessed 2026-09-01: current guidance favors vector source, a 1024 x 1024 working canvas for iPhone/iPad/Mac icon composition, layered artwork, and leaving platform masking/effects to the platform toolchain rather than baking them into source artwork.
- Apple App Store Connect help, accessed 2026-09-01: the app icon is reused across Home Screen, search, notifications, settings, share sheets and TestFlight, so the source mark must survive both large and small contexts.
- WHOOP developer design guidelines, accessed 2026-09-01: a dedicated small-scale icon can coexist with a primary wordmark, with explicit minimum-size and exclusion-zone discipline. Principle adopted, geometry not copied.
- Oura intellectual-property notice, accessed 2026-09-01: brand and UI assets are treated as protected product identity. Principle adopted: avoid competitor trade dress, icon geometry and layout mimicry.
- USPTO Trademark Official Gazette, 2024-11-19: `MASCK`, US serial 79306463, International Registration 1580707, standard-character mark, was published for opposition. Listed goods/services include downloadable software and software applications for assessing skin cancerization and damage, plus medical/skin-related content and assessment uses.
- IP Australia Australian Trade Mark Search guidance, accessed 2026-09-01: ATMS is the official system for searching registered and pending marks and supports searches by word, phrase, image, owner, goods/services and trade mark number. IP Australia explicitly cautions that search results do not guarantee an examination outcome.
- Public Australian index record cross-check, accessed 2026-09-01: Australian application 2142822 is reported for the word mark `MASCK`, including classes 009, 016, 042 and 044. This third-party status record is treated as a lead requiring confirmation in ATMS, not as legal clearance or an infringement conclusion.

## Masck One decision

Use a dedicated symbol for favicon/app/social use while retaining the current typographic MASCK ONE wordmark in interface copy. Do not freeze a custom outlined wordmark until typography is production-locked.

The primary symbol route remains a two-field seam concept derived from the product grammar rather than a letterform. The original straight central split was rejected after hostile review because it collapsed toward a generic pause/control glyph at favicon scale. The revised candidate uses two asymmetric soft engineered fields and a controlled flowing seam. The seam changes direction through the vertical axis while the outer envelope stays calm and low-complexity. This preserves compliant-versus-rigid and soft-versus-controlled structure without relying on a face, eyes, medical cross, ring, shield, sparkle, heart, droplet or monogram.

Source geometry remains flat SVG with no blur, gradient, baked platform mask, shadow or simulated material effect. Platform-specific optical effects are downstream presentation decisions.

Current palette is inherited from the released Cell 2 digital surface, not invented here: field `#e8e5dc`, ink `#1d211f`, controlled green `#314f38`.

## Distinctiveness challenge

The selected route was challenged against likely small-scale visual confusions:

1. Pause/control symbol: rejected straight parallel fields. Revised seam must visibly change direction and the two fields must not read as equal bars.
2. Split capsule/pill: rejected closed shared capsule envelope and uniform bilateral symmetry. Revised fields keep independent outer contours and unequal inner curvature.
3. Generic dual-panel app icon: rejected equal rectangles/pills and arbitrary rounded-square dependence. The mark must remain identifiable without its platform container.
4. Four-zone/grid device symbol: retained only as a secondary explanatory motif because quadrant geometry reads too readily as software navigation or medical zoning.
5. M1 monogram: retained as rejected because it is typography-dependent and less product-specific.

Observable pass criteria for the revised candidate:

- at 16, 20, 24 and 32 px, the negative seam remains open and does not collapse into one mass;
- the symbol does not resolve primarily as two equal parallel bars;
- monochrome and reversed treatments preserve the same negative seam topology;
- app-mask cropping cannot remove the seam endpoints or convert the mark into a generic pill;
- favicon, app-icon, social-avatar and OG sources share the same canonical path geometry;
- no platform container is required to make the mark recognizable.

These are design-verification criteria, not evidence of trademark distinctiveness in a legal sense.

## Collision and legal-risk screen

The earlier wording that described `MASCK` as merely an unrelated clinical acronym was too weak. The current evidence shows a named skin-assessment mark with materially adjacent software and skin/medical goods/services. For a skin-adjacent consumer device with a companion app, that is sufficient to treat the name as an explicit brand-launch risk requiring formal review.

Known identifiers to carry forward:

- US serial: 79306463
- International Registration: 1580707
- Australian application lead: 2142822
- Literal mark: `MASCK`

No conclusion is made here about infringement, registrability, ownership conflict or likelihood of confusion. The product name `MASCK ONE` is not declared cleared.

Hard gate before public launch, paid acquisition, packaging production, manufacturing mark application or expensive final brand rollout: confirm the Australian record in official ATMS, search relevant classes and similar marks/phonetic variants in Australia and intended launch jurisdictions, then obtain qualified trademark advice on the actual goods/services and proposed use.

## Asset policy

- `brand-mark.svg` is the canonical split-retained symbol source and must be byte-identical in web and app workspaces.
- `brand-mark-mono.svg` uses identical path topology in one color.
- `favicon.svg` uses the canonical mark in a browser-scale presentation container; the container is not part of mark geometry.
- `app-icon-source.svg` is a 1024 x 1024 unmasked source composition, not a final App Store deliverable.
- `social-avatar-source.svg` carries the same path geometry and optical placement as the app-icon source.
- `og-source.svg` is an editable social-card source template, not evidence of product availability.
- Raster favicon, Apple touch icon, store-ready icon set and platform-specific launch images remain downstream exports after final optical review and platform validation.
