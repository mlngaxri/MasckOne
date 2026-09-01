# Cell 4 commercial burden benchmark

Date: 2026-09-01
Region of primary commercial interpretation: Australia
Status: public-evidence benchmark only. This document does not approve suppliers, set retail price, assert final battery runtime, or authorize product claims.

## Purpose

This benchmark converts current premium wearable, beauty-tech and consumer-hardware service patterns into explicit MASCK ONE commercial burden constraints. It is an engineering input, not a market-positioning claim. Public retail and support evidence is used only to understand recurring burden, charging expectations, app dependence, return/service flows, and replacement expectations.

## Current public evidence

### Oura

Oura currently states Ring 5 typical battery life of 6 to 9 days and Ring 4 typical battery life of 5 to 8 days, with a full charge taking roughly 20 to 80 minutes depending on state of charge. Oura also explicitly states that actual battery life varies with configuration, use, battery age and other factors. Source checked 2026-09-01: https://support.ouraring.com/hc/lv/articles/4408961184147-General-FAQs

Oura's Australian membership is publicly listed at AUD 9.99 per month or AUD 109.99 per year, and app membership features are tied to the account. This is a useful example of a technically successful premium wearable carrying recurring software burden, but it is not evidence that MASCK ONE users will accept such a burden. Source checked 2026-09-01: https://ouraring.com/es/membership and https://support.ouraring.com/hc/en-us/articles/4409086524819-Oura-Membership

Oura supports Australian self-service returns/exchanges and states a 30-day refund window for eligible direct purchases, with prepaid return labels. Source checked 2026-09-01: https://support.ouraring.com/hc/en-us/articles/1500006009441-Return-or-Exchange-an-Oura-Product

### Therabody

TheraFace Mask publishes an approximately 120-minute LED-mode battery life, 60-minute vibration-mode battery life, USB-C charging cable inclusion, and a device weight of 576 g. This demonstrates that premium facial hardware can tolerate relatively frequent charging when the usage session is short, but MASCK ONE's wet fluidic architecture creates substantially higher service and contamination burden than an LED mask. Source checked 2026-09-01: https://www.therabody.com/products/theraface-mask

Therabody's current return policy allows eligible direct purchases to be returned within 30 days, subject to condition and packaging requirements. Its published warranty framework generally gives devices a one-year limited warranty and accessories shorter coverage. Source checked 2026-09-01: https://www.therabody.com/pages/return-policy and https://www.therabody.com/pages/warranty-terms

### CurrentBody

CurrentBody Australia publicly states a standard two-year warranty for manufacturing faults and documents a conventional customer-care return workflow. This is relevant because facial beauty-tech purchasers are already exposed to multi-year device-support expectations even where the product is not mechanically serviceable by the user. Source checked 2026-09-01: https://www.currentbody.com.au/pages/delivery-returns

### Apple

Apple Watch uses a dedicated magnetic charging interface with USB-C cabling and provides explicit battery-health, low-power, charging-fault and service pathways. Apple also publicly provides battery service and states that Apple Watch batteries are designed to retain up to 80 percent of original capacity at 1,000 complete charge cycles. These are reference expectations for fault recovery and long-term support, not a requirement to copy Apple's proprietary charging architecture. Sources checked 2026-09-01: https://support.apple.com/en-au/108760, https://support.apple.com/en-au/108927, https://www.apple.com/au/batteries/service-and-recycling/, https://support.apple.com/en-au/watch/repair

### Dyson Australia

Dyson Australia offers a 30-day money-back process for eligible direct purchases and maintains explicit repair/service channels, including approved service agents and a service centre. Its support model is relevant to MASCK ONE because higher-value hardware with wet, mechanical or contamination-prone subsystems creates an expectation that failure resolution is more substantial than a generic email-only warranty process. Sources checked 2026-09-01: https://support.dyson.com.au/orderanddeliveryinformation and https://support.dyson.com.au/support/repairsandservicinginformation

## MASCK ONE burden ledger

The following are controlled product-development gates. Values not yet physically demonstrated remain targets or unresolved states, not claims.

| Burden | Cell 4 commercial interpretation | Required engineering treatment before release |
| --- | --- | --- |
| Water refill | A refill every cleansing session may be acceptable if the action is obvious, fast and spill-resistant. Multiple partial refills per session are commercially poor. | Demonstrate usable volume, residual volume, fill ergonomics, fill-time distribution and spill recovery on alpha hardware. |
| Cleanser refill | Requiring proprietary cleanser would create recurring-cost and logistics burden. Claiming universal cleanser compatibility without testing is unacceptable. | Maintain user-cleanser architecture where practical. Build a bounded viscosity/surfactant/material compatibility test matrix before compatibility claims. |
| Waste handling | Waste service is qualitatively more burdensome than charging. Frequent dirty-liquid handling or hidden retained liquid is a major adoption risk. | Quantify gross, usable, dead, residual and retained waste volumes separately. Demonstrate removal, sealing, drainage, drying and contamination recovery. |
| Disposable cartridge | A cartridge can reduce hygiene burden but adds recurring cost, fulfillment complexity and stock-out risk. | Do not lock a disposable cadence until physical waste loading, foam, microbial/hygiene and service trials establish a defensible interval. Compare reusable and disposable pathways. |
| Charging | Premium wearables span daily-ish charging through multi-day cadence. MASCK ONE should not assume multi-day endurance without a closed energy ledger and measured load profile. | Publish no exact runtime until battery, pump, actuator, electronics and standby measurements are integrated. Prefer standard USB-C input where architecture permits, while keeping wet-zone isolation explicit. |
| App requirement | Mandatory subscription/app dependence increases setup, account and failure-recovery burden. | Core cleanse, stop, fault-clear and service functions must remain locally operable unless a later safety case proves otherwise. SimulatedTransport must remain explicit simulation until real transport exists. |
| Cleaning | The wet path creates burden absent from Oura/Apple and greater than LED masks. | Define cavity hygiene classes, drain/dry intent, accessible surfaces, maximum user cleaning steps, and fault recovery for retained fluid. Validate with physical soiling and drying tests. |
| Setup | Premium consumer hardware generally minimizes repeat setup after onboarding. | Cartridge, reservoir and cleanser operations require keyed, low-ambiguity insertion states and explicit error recovery. App setup cannot be required for basic safe service. |
| Travel/storage | Wet retained volume, accidental actuation and leakage make travel more difficult than dry wearables. | Add verified transport state, drain/dry procedure, actuation lockout and storage orientation instructions before travel claims. |
| Warranty/service | Current premium hardware commonly exposes clear return and service pathways, with one to two year device warranties visible in the benchmark set. | Commercial plan must define Australian Consumer Law handling, DOA flow, contamination-safe return packaging, triage, refurbishment/disposal boundaries and spare/replacement policy before paid launch. |

## Commercial architecture decisions now justified

1. No subscription is required for core cleansing functionality in the current architecture. A subscription would add recurring software burden without presently demonstrated user value.
2. No proprietary-cleanser lock-in is justified by current evidence. The architecture should preserve compatibility testing around user-supplied cleansers while refusing any universal-cleanser claim until physical validation closes viscosity, foaming, elastomer, film, pump and residue constraints.
3. USB-C is the preferred external charging convention if electrical and ingress architecture permit it. A proprietary exposed wet-zone connector is disfavoured because it adds cable replacement and service burden without a demonstrated engineering advantage. This is a design preference, not a frozen electrical implementation.
4. Waste service burden is the dominant commercial risk unique to MASCK ONE. Any architecture that saves small internal volume but increases dirty-liquid handling, retained liquid, seals, connectors or cleaning steps must show a material performance advantage before adoption.
5. Disposable cadence must remain evidence-gated. Retail pricing of adjacent products is not a defensible basis for cartridge economics or cadence.
6. Exact battery runtime, refill cadence, cartridge cadence, cleanser compatibility and orientation claims remain prohibited until measured evidence exists.

## Required burden acceptance tests for physical alpha

For each alpha participant and each scripted cycle, record: water fill time, cleanser fill/service time, number of user actions, number of ambiguous or failed insertions, visible spills, recovered spill mass/volume, post-cycle drain time, residual liquid by subsystem, cleaning time, drying time, odor/visible residue observations, charge state before and after cycle, fault-clear steps, and whether the cycle could be completed without the app.

At minimum, evaluate nominal use plus deliberately adverse states: underfill, overfill where physically possible, partial cartridge insertion, reservoir reseat, foaming cleanser, high-viscosity cleanser within the approved test range, interrupted cycle, low battery, post-cycle storage, and travel-lock/storage preparation. These are validation scenarios, not consumer instructions.

## Release firewall

The website and app may not infer or advertise: leak-proof operation, universal cleanser support, an exact number of cycles per charge, an exact refill interval, an exact cartridge replacement interval, orientation independence, maintenance-free operation, skin-safe temperature, or guaranteed efficacy from this benchmark.

Commercial comparisons in this document are burden references only. They do not establish MASCK ONE equivalence to Oura, Therabody, CurrentBody, Apple or Dyson, and they do not establish willingness to pay, warranty cost, BOM, margin or production economics.
