# Masck One brand usage v0.1

Status: controlled digital candidate, not final trademark clearance and not a production CMF or hardware-marking release.

## Mark concept

The selected candidate uses two rounded fields divided by one controlled seam. The left field represents compliant contact behavior and the right field represents controlled rigid structure. The seam is the identity-bearing element: it should remain visible at small sizes and must not be filled, bridged or converted into a generic pill.

Three routes were considered before selection:

1. Split-field seam. Selected because it derives directly from the compliant-versus-rigid product grammar, remains legible without text and avoids face, eye, medical and VR symbolism.
2. Four-zone aperture. Rejected for primary identity because a quadrant/grid construction reads too close to generic software navigation or medical zoning, despite reflecting the four cleansing zones.
3. M1 monogram. Rejected for primary identity because it depends on typography, is less product-specific and creates a higher risk of generic technology-brand behavior.

## Observable criteria

- canonical symbol source uses two filled paths and one negative-space seam;
- no face, eye, cross, shield, sparkle, droplet or ring silhouette;
- no gradient, blur, shadow, baked platform mask or simulated material effect in canonical source;
- symbol remains recognizable in a 20 CSS pixel digital box; below that size, use the dedicated favicon composition rather than modifying geometry;
- web and app canonical `brand-mark.svg` files must remain byte-identical;
- source mark may appear in controlled green plus ink, or as the monochrome source; do not recolor individual lobes independently;
- minimum clear space around a standalone mark is one eighth of the symbol box width;
- do not place the mark inside an additional arbitrary rounded rectangle except where an operating system, browser or export format requires a container;
- do not rotate, skew, outline, add facial apertures or combine the mark with unverified product geometry.

## Palette use

The digital candidate inherits released Cell 2 surface colors: field `#e8e5dc`, ink `#1d211f`, controlled green `#314f38`. These are digital presentation colors only and must not be represented as frozen physical CMF.

## Asset roles

- `brand-mark.svg`: canonical two-color symbol source.
- `brand-mark-mono.svg`: one-color source for monochrome or reversed export. White reversal is an export treatment of this geometry, not separate geometry.
- `favicon.svg`: browser-scale composition with field background.
- `app-icon-source.svg`: 1024 by 1024 unmasked source composition. Platform masks and rendering effects are applied downstream using current platform tooling.
- `social-avatar-source.svg`: square social-profile source using the same optical placement as the app-icon source.
- `og-source.svg`: editable social-card source. Its development disclaimer is mandatory until claims governance releases stronger public copy.

## Wordmark

The current interface wordmark remains typographic `MASCK ONE`. A custom outlined wordmark is intentionally not frozen in v0.1 because final production typography has not been locked. Do not convert the current system-font rendering into permanent logo outlines.

## Legal status

A basic current-web collision screen found an unrelated `MASCK` clinical assessment mark/acronym. This is not a finding of infringement and not clearance. Formal trademark searches by class and jurisdiction, counsel review and filing strategy remain required before public launch or manufacturing mark application.
