# MASCK brand source layer

This directory holds human-reviewable source assets for the **MASCK** master brand and its product-family identity.

The repository deliberately separates three things:

1. `MASCK` is the parent brand and long-term company identity.
2. `Masck One` is the founding hero product.
3. `M/1` is a compact product designation, not the master company logo.

The current standalone master-mark direction is `M_CUT`: a calm M with a distinctive central negative incision. The exact vector geometry remains a **provisional master-mark candidate** until dedicated identity review and trademark clearance.

Machine-readable brand/product intent lives in [`../config/masck_brand_authority.yaml`](../config/masck_brand_authority.yaml) and is structurally validated by [`../schemas/masck_brand_authority.schema.json`](../schemas/masck_brand_authority.schema.json). Code consumers must use [`../src/masck_one/brand_identity.py`](../src/masck_one/brand_identity.py) rather than creating a second palette, naming system or HMI-brand truth.

## Asset status

- `assets/masck_m_cut_candidate.svg`: provisional master-mark geometry. It may be refined or replaced without changing the parent-brand architecture.
- `assets/masck_one_m1_candidate.svg`: derived product designation showing how the master geometry can seed an `M/1` badge.

These vectors are identity-study assets, not tooling drawings, mold geometry, optical-performance evidence or trademark registration evidence.

## Brand architecture

**Master brand:** MASCK  
**Master mark:** M-Cut  
**Founding product:** Masck One  
**Compact product designation:** M/1  
**Long-term territory:** premium automated personal-care hardware  
**Near-term execution:** Masck One remains the overwhelmingly important product.

## Physical-product rule

The master mark should become part of the object rather than printed decoration where the architecture supports it. The primary control is the preferred signature location: microtexture or shallow surface contrast can form the M while a flush optical feature can inhabit the central cut. The button must still be designed first as a reliable, low-rattle, sealed physical mechanism.

Brand intent never overrides engineering safety, geometry, service, manufacturing, electrical/thermal/wet-use constraints or physical-validation gates.
