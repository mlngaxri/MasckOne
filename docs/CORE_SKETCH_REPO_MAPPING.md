# MASCK ONE Core Sketch Repository Mapping

Status: **ownership map; refresh against live GitHub before acting**  
Date: 2026-09-10

This file maps Core Sketch work to the established repository owner-lane pattern. Branch/PR numbers below are navigation clues only and may become stale. Live GitHub always wins.

## Existing subsystem ownership that must be reused

### Primary HMI / signature control

Historical owner lineage: PR #144, `codex/buttery-primary-hmi-20260909`.

Core Sketch items:

- CS-034 temple/control composition
- CS-064 motion-quality grammar
- CS-200 primary-button force-path correction
- CS-201 tactile target
- CS-202 control accessibility

Do not create a parallel primary-button architecture while this lineage remains current.

### Treatment / massage interface

Historical owner lineage: PR #135, `codex/treatment-live117-reconcile-20260909`.

Core Sketch items:

- CS-120 cleanse sensation
- CS-130 massage role
- CS-131 massage comfort envelope
- CS-132 massage acoustics
- CS-160 non-wiping state only where it shares treatment/interface geometry

Existing exact-collision/evidence work remains authoritative for current treatment geometry. Do not weaken protected anatomy to make new leave-on concepts fit.

### Retention / quick release / whole-head removal

Historical owner lineage: PR #141, `sol-high/retention-quick-release-20260909`.

Core Sketch items:

- CS-052 retention UX
- CS-180 non-wiping release path
- CS-181 emergency release
- CS-182 normal release feel

The new leave-on requirement expands the acceptance criteria of release; it does not justify a second retention architecture.

### Waste cartridge / service

Historical owner lineage: PR #140, `sol-high/cartridge-service-20260909`.

Core Sketch items:

- CS-105 waste concealment/service
- CS-194 waste service experience
- related dock return/service choreography.

Preserve the supported-liner / cavity / premium blind-service owner work and extend only through the canonical lineage.

### WARM / thermal package

Historical owner lineage: PR #143 / released package later bound through integration work. Live state must be checked.

Core Sketch items:

- CS-140 deliberate WARM
- CS-141 COOL
- CS-142 incidental heat budget

Do not revive an older thermal candidate if a released package is now canonical.

### Dry-side / power / electronics packaging

Historical owner lineage: PR #142, `cell12/compact-dry-side-package-reconstructed-20260909`.

Core Sketch items:

- CS-053 full-routine mass/CG reconciliation
- CS-061 optical/status integration implications
- CS-111 session-dose package location where dry-side packaging interacts
- CS-142 incidental heat.

### Structural frame / reaction loop

Historical owner lineage: PR #117, `cell6/structural-frame-reaction-loop-v1`.

Core Sketch items:

- CS-030 master-surface integration where attachment/reaction geometry constrains ID
- CS-053 mass/CG
- CS-131 massage reaction/comfort dependencies
- CS-270 integrated digital package.

### Whole-product conductor / integration

Use the current integration/freeze lineage that owns canonical registry/source binding on live main.

Core Sketch items:

- CS-270 integrated digital package
- CS-271 routine-phase digital review
- CS-274 product-truth review.

Do not let an individual subsystem branch become whole-product authority.

## Genuinely new owner areas created by the full-routine concept

These need a canonical owner lane when work begins; do not split each into multiple experimental PRs unless the existing governance explicitly supports candidate branches.

### Full-routine application / leave-on platform

Owns:

- CS-010 reduced full-routine rig coordination
- CS-012 leave-on survival
- CS-013 multi-product contamination
- CS-014 product-family envelope
- CS-160..165 leave-on application.

This lane should interface with treatment, fluidics and retention owners rather than replacing them.

### Product compatibility / database

Owns:

- CS-080..086
- product identity/evidence/profile schema
- unknown-product bounded classification
- reformulation tracking
- community-learning data model.

### Routine OS / scheduling

Owns:

- CS-020..022 state model at product/software boundary
- CS-090..096 routines/schedules/overrides/offline cache
- CS-210 readiness summary.

### Dock product architecture

Owns product-level dock composition and coordinates existing cartridge/thermal/dry-side/service owners:

- CS-070 bulk-slot count
- CS-100..108 dock UX
- CS-110..113 session-dose preparation.

### Facial SPF proof

Owns:

- CS-170..175
- claims/regulatory/application validation

This should remain deliberately separate from generic leave-on success until SPF-specific proof exists.

### Optical treatment

If no canonical optical owner currently exists, create one only after CS-150/151 define claims/output targets. Owns CS-150..155.

## Rule for new branches

A new branch is justified only when:

- the backlog work is genuinely unowned;
- no existing open PR owns the same physical/software truth;
- the new lane has an explicit interface contract with adjacent owners;
- it does not duplicate released main or supersede a current candidate without recording why.

Before using any historical PR/branch above, fetch live GitHub. This file intentionally does not freeze SHAs.
