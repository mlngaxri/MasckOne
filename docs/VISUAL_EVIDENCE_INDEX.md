# Visual evidence index

[Project overview](../README.md) · [Evidence guide](EVIDENCE_GUIDE.md) · [Documentation index](README.md)

This page gives a scholarship reviewer the shortest visual inspection path through the existing repository. It does not add new engineering evidence. It only surfaces already committed artefacts and their evidence limits.

## 1. Whole-product architecture

```mermaid
flowchart LR
    D["Dock and preparation"] --> P["Product storage and delivery"]
    P --> F["Facial interface and treatment mechanics"]
    F --> W["Waste recovery and cartridges"]
    R["Retention, structure and removal"] --> F
    C["Electronics, controls and software"] --> D
    C --> P
    C --> F
    C --> W
```

This diagram is assembled from the existing [Core Sketch product story](CORE_SKETCH_ONE_PAGE.md) and subsystem documentation. It shows documented subsystem relationships, not proof that every subsystem is implemented or physically validated.

## 2. Representative registered digital compositions

### Front three-quarter

![Front three-quarter registered digital review composition of Masck One](../website/images/masck-inspection-front-3q-v17c.webp)

**What this helps inspect:** candidate face-side packaging, opening layout and the visible relationship between the facial shell and surrounding structure.

**Evidence limit:** concept/candidate digital composition only. It does not prove released-main geometry, anatomical fit, comfort, sealing, treatment coverage or physical performance.

[Open full-resolution view](../website/images/masck-inspection-front-3q-v17c.webp)

### Side-rear

![Side-rear registered digital review composition of Masck One](../website/images/masck-inspection-side-rear-v17c.webp)

**What this helps inspect:** candidate depth, rear packaging and the visible relationship between the face-side body and retention structure.

**Evidence limit:** concept/candidate digital composition only. It does not prove attachment closure, removal behaviour, serviceability, structural strength, manufacturability or safety.

[Open full-resolution view](../website/images/masck-inspection-side-rear-v17c.webp)

The [registered render manifest](../website/images/masck-inspection-v17c-manifest.json) records the asset version, camera definitions, coordinate frame, source checkpoints, image hashes and explicit claim boundary for these compositions. The manifest classifies the exterior and retention geometry as candidate work rather than released-main physical evidence.

## 3. Engineering evidence behind the visuals

The repository does not currently contain a standalone gallery of released-main engineering CAD screenshots. The stronger engineering evidence is source-bound and reproducible rather than presentation imagery.

For a direct inspection path, open the [parametric engineering source](../src/masck_one/), the [engineering authority](../config/masck_one_authority.yaml), the [automated tests](../tests/) and the [engineering quickstart](ENGINEERING_QUICKSTART.md). These can demonstrate controlled digital geometry, provenance and automated checks. They do not establish human fit, comfort, safety, cleaning efficacy, manufacturability or physical product performance.

For the fuller explanation of evidence classes, development progression and validation boundaries, continue to the [evidence guide](EVIDENCE_GUIDE.md).
