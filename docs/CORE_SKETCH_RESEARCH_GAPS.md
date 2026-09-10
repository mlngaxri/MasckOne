# MASCK ONE Core Sketch Research Gaps

Status: **open research register**  
Date: 2026-09-10

This file lists questions that should be answered with external research, bench work, human factors, regulatory guidance or supplier evidence before later teams over-specify them from intuition.

## Human factors / anthropometry

- adult facial anthropometry suitable for a limited-size wearable family;
- eye-opening / visual-field implications across face sizes;
- pressure tolerance and retention comfort over intended routine duration;
- long-hair / earring / glasses interaction;
- dynamic comfort while talking, moving head and walking indoors;
- acceptable local skin-contact pressure and pressure-mark recovery;
- user perception thresholds for incidental warmth, vibration and mechanism noise.

## Skincare formulation/application

- practical viscosity/rheology/particle-size envelope across popular cleansers, essences, serums, lotions, creams and sunscreens;
- how common formulations respond to repeated pumping, shear, storage in small reservoirs, temperature cycling and exposure to device-path materials;
- realistic per-face dose distributions by product type without assuming retail directions are physically interchangeable;
- layer interaction/settling behavior for common sequences;
- objective ways to assess even leave-on coverage without turning the product into a diagnostic skin scanner;
- representative compatibility test set for launch-market products.

## Cleansing / barrier

- suitable gentle-manual comparator for Masck cleansing studies;
- objective residue-removal and skin-barrier/hydration metrics;
- appropriate duration/frequency limits;
- effects of mechanical treatment plus cleanser versus cleanser alone;
- cleanser carryover thresholds before leave-on application.

## Sunscreen

- current Australian/TGA and target-market requirements for sunscreen/application claims;
- appropriate validation method for an automated application device using third-party sunscreen products;
- final-film uniformity measurement across nose, periorbital, hairline and mouth boundaries;
- face-area/dose handling across users;
- product-family differences including mineral-heavy, fluid and emulsion sunscreens;
- eye/airway exposure limits and user instructions;
- reapplication and timing language that can be safely represented in software.

## Optical treatment

- claim-led wavelength/dose evidence rather than competitor-led specification;
- eye-safety standards/exposure assessment for visible red and NIR bands;
- field uniformity requirements over curved/variable face distance;
- thermal contribution of optical subsystem;
- user ability to look at screens / keep eyes open under final optical architecture;
- whether ~1072 nm provides enough differentiated value to justify cost/thermal complexity.

## Thermal treatment

- perceptual and comfort range for deliberate WARM/COOL;
- incidental warmth threshold that users notice as device heat;
- skin-contact uniformity and hot/cold spot tolerances;
- condensation risk for COOL in humid wet-use conditions;
- whether users value WARM/COOL enough to justify integration complexity.

## Product identification / database

- barcode/SKU coverage across AU/US/UK/EU/Korean/Japanese skincare markets;
- product reformulation/version detection methods;
- public/manufacturer data licensing and reliable ingredient-source strategy;
- privacy-preserving aggregate application telemetry;
- evidence standard for promoting CHARACTERISED to VALIDATED;
- legal/product-liability implications of supporting third-party products;
- wording that distinguishes “recognized” from “validated for automatic application.”

## Dock / ownership

- real-world bathroom-vanity footprint expectations;
- acoustic expectations for bedroom placement;
- user willingness to refill multiple bays versus insert original product containers;
- acceptable waste-emptying cadence;
- service interaction frequency that still feels premium;
- spill/error modes during filling;
- long-term odor/staining/cleaning behavior.

## Materials / CMF

- cosmetic-grade production materials that can achieve the selected Mineral Ivory / Warm Porcelain / Soft Stone / Smoke Graphite palette;
- chemical resistance to cleanser, sunscreen, oils, acids, retinoid formulations and household cleaning agents;
- sweat/sebum staining and yellowing;
- satin-matte surface durability;
- skin-contact friction/tack when dry, damp and product-coated;
- cleaning method compatible with premium appearance over life.

## Accessibility / privacy

- device-state semantics that remain understandable without color or sound;
- one-handed refill/service ergonomics;
- low-vision tactile loading patterns;
- minimum camera/data collection required for product identity;
- offline product-profile cache and update model;
- deletion/export/consent design for optional product-learning telemetry.

## Commercial/product validation

- whether target skincare enthusiasts actually prefer full automation to manual ritual;
- which step creates the greatest perceived value: time saving, consistency, no sink, no hand application, optical treatment, massage or portability;
- whether users trust automated use of their existing skincare;
- what compatibility coverage is required at launch to make the promise credible;
- willingness to accept a 2–3 size family;
- price elasticity once the object and routine are demonstrated physically.

Research conclusions that materially affect the Core Sketch should be added to `CORE_SKETCH_DECISION_LOG.md` and converted into/close backlog items. Do not silently replace the concept based on a single paper, competitor claim or anecdote.
