# Cell 4 Physical Validation, Procurement and Compliance Roadmap

Date: 2026-09-01
Status: CONTROLLED PLANNING DOCUMENT, NOT SUPPLIER APPROVAL, NOT COMPLIANCE CERTIFICATION
Scope: fresh and waste fluidics, wet/dry segregation, battery/electronics, service and hygiene validation, prototype procurement, test-lab engagement and evidence gates for MASCK ONE digital-alpha exit.

## 1. Evidence boundary

This roadmap converts the current digital architecture into a physical-validation sequence. It does not promote benchmark parts, public supplier claims, CAD dimensions, simulated volumes or consumer-hardware comparisons into measured MASCK ONE performance.

No pump, battery, elastomer, film, cleanser, cartridge media, electronics manufacturer, prototype house or test laboratory listed here is an approved supplier. Approval requires controlled samples, supplier evidence, incoming inspection, fit/function testing and the relevant engineering release gate.

No statement in this document establishes that MASCK ONE is leak-proof, orientation-independent, universally cleanser-compatible, thermally skin-safe, capable of an exact runtime or cartridge cadence, or compliant with a named standard.

## 2. Physical-alpha sequence

### Alpha 0A: material and fluid coupons

Procure before an integrated wearable build:

- representative compliant-interface silicone or elastomer coupons in at least three bounded hardness/thickness combinations selected by mechanical engineering;
- representative rigid enclosure coupons in candidate production polymer families, with molded-equivalent surface finishes where practical;
- representative tube, manifold, seal and connector coupons for every wetted material family;
- fresh-fluid reservoir and waste-contact coupons with production-intent joining methods where possible;
- battery dummy masses and geometric surrogates before live cells are placed near wet systems;
- controlled reference fluids spanning low viscosity, bounded cleanser-like viscosity and intentionally foaming conditions without claiming universal cleanser coverage.

Required outputs: mass, dimensional inspection, wetting/retention observations, swelling or softening observations, odor/discoloration notes, dry-out behavior, cleanability observations and explicit reject/continue decisions. Coupon results remain material-system evidence only and cannot be promoted to whole-device claims.

### Alpha 0B: isolated fresh-fluid bench

Build the water and cleanser routes separately before combining them with the facial interface. Required instrumentation should support, as applicable, gravimetric dose measurement, pressure measurement, current logging, supply-voltage logging, temperature logging, transparent route observation and captured-effluent mass.

Minimum experiments:

1. prime from dry and partially wet initial states;
2. dose repeatability across bounded supply voltage and fluid viscosity;
3. restart after interruption;
4. trapped-air sensitivity;
5. route-elevation and orientation sensitivity;
6. bend-radius and route-length sensitivity around the CAD-controlled nominal;
7. post-cycle residual liquid by segment where physically measurable;
8. connector reseat and reservoir reseat fault cases;
9. bounded foaming-fluid behavior;
10. pump current and local temperature during representative duty cycles.

Digital swept/internal volume stays distinct from measured prime, purge, retained and recoverable volume.

### Alpha 0C: isolated mixed-phase waste bench

The waste path must be tested as an air/liquid/foam/contaminant transport system, not as a single-phase water line. Use transparent or instrumented surrogates before opaque production-intent geometry.

Required experiments:

- ingress capture under multiple source wetness conditions;
- air fraction and foam sensitivity;
- interrupted suction and restart;
- low and high expected liquid loading;
- route high-point and low-point retention;
- pump-in and pump-out fault simulations where physically safe;
- cartridge insertion, partial insertion and removal states;
- full, near-full and intentionally over-limit surrogate cartridge states;
- post-cycle drain/dry behavior;
- spill containment and wet/dry boundary challenge using nonhazardous test liquid;
- retained-liquid mapping after storage in multiple bounded orientations.

No capacity release occurs from cartridge gross geometric volume alone. The ledger must separately report gross/internal, absorbent or capture-media nominal capacity if present, usable capacity, dead volume, retained liquid, residual liquid, safety reserve and rejection threshold.

### Alpha 0D: wet/dry segregation mule

Use an electronics-safe mule with passive leak witness media or equivalent detection around dry cavities. Live battery integration is not required for the earliest segregation tests.

Challenge cases should include reservoir underfill/overfill within physically safe fixture limits, connector mis-seat, cartridge mis-seat, interrupted cycle, service access while wet, controlled route leak, storage after a wet cycle and cleaning/drying misuse cases that are reasonable to anticipate.

Acceptance is not zero visible liquid everywhere. Acceptance requires that each cavity has an assigned hygiene class and wet/dry intent, fault liquid has an intentional containment/drain path, dry-zone ingress limits are quantified, inspection access is defined and recovery steps are realistic for a consumer product.

### Alpha 1: powered integrated engineering prototype

Only after isolated fluid benches and segregation mules have bounded the dominant risks should the program combine pumps, control electronics, battery, structural packaging, fluid storage, facial interface and waste system.

Capture synchronized current, battery voltage, relevant temperatures, state transitions, fluid masses and fault logs. Any website/app payload generated from this prototype must identify the transport as simulated unless real hardware telemetry is deliberately implemented and validated. No fabricated BLE or sensor capability is permitted.

## 3. Procurement classes and candidate references

### 3.1 Pump references

KNF liquid diaphragm pumps are a credible engineering reference because KNF publicly documents OEM liquid-pump families, self-priming/dry-running capability and customization, including small liquid-pump products. Reference only: https://knf.com/en/global/solutions/technology/liquid-diaphragm-pumps and https://knf.com/en/au/solutions/pumps/series/diaphragm-liquid-pump-fp-7

Bartels Mikrotechnik BP7 is a separate miniature piezoelectric reference. Public information describes a compact liquid/gas pump, self-priming behavior, low internal volume, STEP data and OEM integration material. Reference only: https://bartels-mikrotechnik.de/piezoelectric-pump/

Before either family advances beyond benchmark status, request: exact liquid-media compatibility, pressure-flow curves at candidate drive conditions, dose-repeatability data, startup behavior with air, allowable dry-run conditions, acoustic/vibration data, package tolerances, port loads, lifecycle methodology, temperature limits, wetted-material declarations, sample lead time and commercialization/MOQ constraints.

### 3.2 Electronics and battery integration

Circuitwise Group is a credible Australia/New Zealand electronics design/manufacturing engagement candidate. Public information states product design, PCBA, box-build and test-system capabilities and identifies certified quality systems across relevant business units, including ISO 9001 and ISO 13485. This is evidence of public capability, not MASCK ONE qualification. Sources: https://circuitwise.com.au/circuitwise-group/ and https://circuitwise.com.au/

Battery procurement must require, before design freeze: exact cell and pack manufacturer identity, controlled drawing, chemistry, nominal and maximum voltage, capacity tolerance, protection architecture, thermistor strategy if applicable, charge limits, discharge limits, short-circuit/overcurrent/overtemperature protection evidence, cycle-life evidence appropriate to the intended duty, lot traceability, change-notification terms and the applicable UN 38.3 test summary.

IATA's current lithium-battery guidance states that lithium cells and batteries must have evidence of meeting UN Manual of Tests and Criteria Part III subsection 38.3 and that manufacturers/subsequent distributors make the test summary available. Source: https://www.iata.org/contentassets/05e6d8742b0047259bf3a700bc9d42b9/lithium-battery-guidance-document.pdf

IEC/UL 62133-2 is a relevant portable lithium-battery safety reference, but exact end-product applicability and required certification must be determined with the selected compliance lab and target markets. UL reference: https://www.ul.com/services/battery-safety-testing

### 3.3 Rigid plastics, silicone and prototype tooling

Protolabs remains a rapid prototype/bridge-tooling reference for production-like rigid molding and LSR learning, not an automatic production source. Supplier approval requires material traceability, dimensional capability, cosmetic-surface capability, tolerance evidence, joining-process compatibility and unit economics at the intended pilot scale.

For silicone or other compliant-interface suppliers, the RFQ must request grade identity, cure system, hardness tolerance, thickness/process capability, colorant/additive declarations, extractables or skin-contact evidence available for the exact grade, lot traceability, aging/storage guidance, cleaning-chemical compatibility evidence and change-control practices. Generic statements such as 'medical grade' or 'skin safe' are not accepted as sufficient evidence.

## 4. Test-lab and compliance engagement

### 4.1 Australia electrical and EMC classification

Engage an accredited laboratory before freezing charging architecture or labeling. SGS Australia publicly offers electrical safety, EMC and international product certification services. TÜV SÜD publishes Australian market-access support including EMC requirements. References: https://www.sgs.com/en-au/services/safety-testing-and-certification and https://www.tuvsud.com/en/services/product-certification/global-market-access/australia

Do not decide EESS classification from product intuition alone. EESS public guidance states that extra-low-voltage equipment below 50 V AC RMS or 120 V ripple-free DC is not in-scope, while a mains power supply/charger can itself be in-scope. Not-in-scope equipment still carries an electrical-safety responsibility and may have ACMA obligations. Source: https://www.eess.gov.au/equipment/not-in-scope/

The RCM can represent both EESS and ACMA compliance obligations where applicable. Source: https://www.eess.gov.au/rcm/regulatory-compliance-mark-rcm-general/

Required pre-compliance lab question set:

- classify the wearable, supplied charger/power supply if any, cable and accessories separately;
- identify applicable Australian electrical-safety and EMC standards for the exact architecture;
- confirm whether USB-C power architecture changes the equipment classification or only the external power-source burden;
- determine evidence needed for RCM use and Responsible Supplier obligations;
- identify battery-pack and cell evidence expected by the lab;
- identify foreseeable abnormal-operation tests relevant to fluid ingress, charging and thermal faults;
- confirm whether any radio module is present. Current architecture must not assume Bluetooth or other radio capability;
- define pre-scan, engineering test and formal certification sequence.

### 4.2 Ingress, materials and consumer-use validation

Treat ingress testing, skin-contact compatibility, cleaning durability and hygiene as engineering evidence streams even where a specific formal certification is not yet established.

Do not claim an IP rating from informal leak testing. If an IP rating becomes a product requirement, engage a suitable lab to define IEC 60529 test configuration and whether the product is tested powered, unpowered, assembled with service parts and/or after conditioning.

Do not convert a raw material supplier's biocompatibility statement into a finished-product skin-safety claim. Final interface evaluation must include the exact finished material/process, cleaning residues, realistic contact duration, temperature, moisture and mechanical exposure. Regulatory/clinical claims are outside this roadmap and require separate review.

## 5. Instrumentation and fixture procurement checklist

The physical-validation lab should have or source calibrated/traceable equipment appropriate to the uncertainty required by each gate. Minimum categories:

- precision balances suitable for dose and residual-mass work;
- pressure sensors and fittings with range appropriate to expected fresh and waste routes;
- current and voltage logging for pumps, actuators and integrated duty cycles;
- temperature logging at battery, electronics, pumps, fluid-adjacent structure and skin-adjacent surrogate locations;
- transparent tubing/manifold surrogates for mixed-phase observation;
- controllable orientation fixture with repeatable angular positions;
- leak witness media or nonconductive detection method for dry-bay challenge testing;
- camera/video capture for route and foam observations;
- dimensional metrology for tubing IDs/ODs, port dimensions, seal compression surrogates and molded coupons;
- controlled cleaning/drying fixtures and timers for burden studies;
- safe battery containment and charging setup appropriate to the selected cell/pack supplier's requirements.

Every instrument used for a release number must record equipment ID, calibration status, range/resolution, test date, operator, test article revision and raw-data location.

## 6. Minimum producer handoff package after digital-alpha closure

Package A, non-confidential discovery:

- one-page product definition without proprietary mechanism detail;
- product size/mass target ranges explicitly labeled targets rather than achieved performance;
- process families required: rigid molding, compliant molding, fluidics, electronics, battery integration, assembly and test;
- intended prototype/pilot sequence;
- expected quality-system and traceability needs;
- target geography and launch sequence;
- explicit request for capability fit, engineering engagement model and minimum program information.

Package B, under NDA after fit screening:

- controlled CAD and interface-control drawings;
- BOM with supplier-state field: REFERENCE, CANDIDATE, QUALIFIED or RELEASED;
- CTQ list and tolerance rationale;
- fluid route manifest and volume ledger with digital-versus-measured evidence labels;
- wet/dry cavity map and hygiene classes;
- electronics architecture and preliminary power budget;
- battery requirements and evidence checklist;
- assembly flow and service operations;
- alpha validation plan and known failure modes;
- DFM questions and open engineering decisions;
- change-control and IP boundary statement.

Package C, RFQ/NPI gate:

Require written evidence for tooling assumptions, prototype and pilot process, material sourcing, sub-tier control, lot traceability, inspection method, gauge strategy, first-article reporting, nonconformance process, engineering-change handling, production test strategy, yield reporting, warranty-return support, sample lead times and minimum commercial engagement.

## 7. Advancement matrix

Contact producer candidate -> send Package A -> require written process/capability mapping and named engineering owner -> execute NDA only if fit is credible -> send Package B -> require DFM, process-risk register and unresolved-question list -> build controlled Alpha 0/1 articles -> collect inspection and test evidence -> close CTQs and supplier unknowns -> send Package C -> require pilot-quality plan, traceability, tooling and test evidence before any production nomination.

Pump candidate -> send media, flow, pressure, route, duty and package requirements -> require exact part/revision recommendation and controlled technical evidence -> bench test samples -> compare dose, prime, air handling, power, thermal, acoustic and lifecycle risks -> only then nominate a preferred candidate.

Battery candidate -> send electrical, package and duty requirements -> require exact cell/pack drawing, protection architecture, UN 38.3 test summary and safety evidence -> validate charger/BMS integration and thermal behavior -> freeze only after compliance-lab review and change-control terms.

Compliance lab -> send architecture, charging concept, voltage/power data, radio-status declaration and target markets -> obtain written applicability matrix and test sequence -> run pre-compliance -> remediate -> freeze compliance-critical design -> formal testing only on controlled production-intent articles.

## 8. Release gates

Cell 4 physical systems cannot be called mature for production until all of the following are evidenced:

1. measured fresh-route dose/prime/residual behavior over bounded viscosity, voltage and orientation conditions;
2. measured mixed-phase waste behavior including foam, air, interruption and near-full cartridge states;
3. capacity ledger separating gross, internal, usable, dead, residual, retained and reserve volumes;
4. wet/dry segregation challenge with defined fault containment and recovery;
5. measured integrated current/power and local temperatures over realistic duty and fault cases;
6. battery/cell exact identity plus safety and UN 38.3 evidence;
7. documented service, drain, dry, refill, cartridge and cleaning burden from human-executable alpha procedures;
8. supplier status recorded without promoting benchmark parts to approved status;
9. compliance-lab applicability matrix for the exact marketed configuration;
10. no website/app/marketing claim exceeds controlled physical evidence.

Until these gates close, the correct state is VALIDATION_GATED or UNRESOLVED, not inferred success.