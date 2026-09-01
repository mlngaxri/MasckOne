# Cell 2 brand asset research, 2026-09-01

## Scope

Fresh public-source review for small-scale brand assets and launch-source geometry. This is design research, not trademark clearance or evidence promotion.

## Sources and principles

- Apple Developer, Design Resources and Icon Composer, accessed 2026-09-01: current guidance favors vector source, a 1024 x 1024 working canvas for iPhone/iPad/Mac icon composition, layered artwork, and leaving platform masking/effects to the platform toolchain rather than baking them into source artwork.
- Apple App Store Connect help, accessed 2026-09-01: the app icon is reused across Home Screen, search, notifications, settings, share sheets and TestFlight, so the source mark must survive both large and small contexts.
- WHOOP developer design guidelines, accessed 2026-09-01: a dedicated small-scale icon can coexist with a primary wordmark, with explicit minimum-size and exclusion-zone discipline. Principle adopted, geometry not copied.
- Oura intellectual-property notice, accessed 2026-09-01: brand and UI assets are treated as protected product identity. Principle adopted: avoid competitor trade dress, icon geometry and layout mimicry.

## Masck One decision

Use a dedicated symbol for favicon/app/social use while retaining the current typographic MASCK ONE wordmark in interface copy. Do not freeze a custom outlined wordmark until typography is production-locked.

The symbol is derived from the product grammar rather than a letterform: two compliant rounded fields separated by a narrow controlled seam. It represents compliant versus rigid, soft-field curvature versus precise interface separation. It intentionally avoids a face, eyes, medical cross, ring silhouette, shield, sparkle, heart, droplet or generic monogram.

Source geometry is flat SVG with no blur, gradient, baked platform mask, shadow or simulated material effect. Platform-specific optical effects are downstream presentation decisions.

Current palette is inherited from the released Cell 2 digital surface, not invented here: field `#e8e5dc`, ink `#1d211f`, controlled green `#314f38`.

## Collision screen

A current exact-phrase web search for `MASCK ONE` / `MasckOne` did not surface an obvious like-for-like consumer hardware brand in the returned results. It did surface the unrelated `MASCK` clinical assessment acronym/mark used for Method of Assessing Skin Cancerization and Keratoses. This is enough to prohibit any claim of legal clearance.

Status: basic current-web collision screen only. Formal trademark clearance, class analysis, jurisdictional search, counsel review and filing strategy remain later legal work.

## Asset policy

- `brand-mark.svg` is the canonical split-retained symbol source and must be byte-identical in web and app workspaces.
- `app-icon-source.svg` is a 1024 x 1024 unmasked source composition, not a final App Store deliverable.
- `og-source.svg` is an editable social-card source template, not evidence of product availability.
- Raster favicon, Apple touch icon, store-ready icon set and platform-specific launch images remain downstream exports from these vector sources after final icon optical review.
