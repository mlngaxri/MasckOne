# MASCK ONE Core Sketch Triage Index

Status: **navigation index**  
Date: 2026-09-10

This file is deliberately short. It tells any contributor which document to open first and what each one means.

## Product-definition stack

1. **`docs/CORE_SKETCH_V1.md`** — selected stable product-experience sketch. Read before changing what Masck One is supposed to be or feel like.
2. **`docs/CORE_SKETCH_EXECUTION_BACKLOG.md`** — product-wide dependency-ordered backlog. Read before choosing what to work on next.
3. **`docs/PRODUCT_CONCEPT.md`** — earlier concept-evolution record. Useful context, superseded where the Core Sketch v1 is more specific.
4. **`docs/research/CORE_SKETCH_DEEP_RESEARCH_2026-09-10.md`** — complete preserved research archive, including rejected/superseded ideas. Never treat appearance in this archive as selection.
5. **`docs/DIGITAL_PRODUCT_VISION.md`** — app/site/backend vision downstream of the physical product concept.

## Truth hierarchy

The files above are product intent and orchestration. They do **not** override:

- `config/masck_one_authority.yaml`;
- its schema and semantic checks;
- released source/CAD;
- accepted validation evidence;
- engineering governance.

## Work-selection rule

For a broad instruction such as “continue,” “perfect Masck,” or “do the next most important task”:

1. reconstruct live `main`, current owner PRs and CI;
2. read `CORE_SKETCH_V1.md`;
3. read `CORE_SKETCH_EXECUTION_BACKLOG.md`;
4. pick the highest-priority non-DONE item whose dependencies are satisfied;
5. continue the existing subsystem owner lineage if one exists;
6. create a new owner lane only for genuinely unowned work;
7. preserve physical-evidence gates;
8. update backlog status only when evidence changes.

## Core invariants

Do not casually change:

- complete supported facial skincare routine in one wear session;
- no required face-touch step after normal completion;
- user’s own skincare rather than proprietary lock-in;
- dock-held bulk product with session quantities on-head;
- calm premium personal-care exterior, not VR/PPE/medical/gaming;
- large clean eye openings and real airway;
- offline physical operation and emergency release;
- quiet Opal-neutral sensory language;
- non-wiping leave-on application/release;
- evidence honesty.

Any proposed change to these invariants needs an explicit product-concept decision, not an incidental subsystem PR.
