# Customer discovery

[Project overview](../README.md) · [Documentation index](README.md)

This note records my current customer hypothesis and the questions that should shape the first product. It does not change engineering authority or establish market demand.

## Initial customer and feedback

The initial target is people who already follow multi-step facial-skincare routines and would value spending less active time on repetitive steps. This is a customer hypothesis to investigate, not a validated market segment.

In September 2026, I ran an informal survey of around 20 people highlighted time savings and convenience, including being able to do another activity while a routine runs. Reported concerns were comfort, maintenance and price.

I have not attached the underlying questionnaire, recruitment method or response data to this note, so the feedback cannot be independently assessed here. There are no conversion rates, pricing conclusions or representative-demand claims to infer from it. No respondent identities or invented quotations are published.

## Next research questions

| Topic | What to learn | Useful evidence to retain |
| --- | --- | --- |
| Existing behaviour | Which steps take effort, get skipped or cause frustration? | Anonymised interview notes about current routines and recent examples |
| Initial use case | Which single task offers enough benefit to justify a wearable? | Recurring needs, alternatives and reasons to reject the concept |
| Adoption | How would wearing, preparing, storing and cleaning a device affect the benefit? | Specific objections and conditions for changing an existing habit |
| Price and alternatives | What do people currently buy, and what would the device replace? | Purchasing context; stated interest kept separate from actual purchase behaviour |
| Commercial feasibility | How do plausible manufacturing and ownership costs compare with customer value? | A cost model with sourced inputs and explicitly unresolved assumptions |

Structured discovery should examine existing behaviour before asking for reactions to the proposed solution. Record the method, sample limitations and contradictory feedback alongside positive comments. Interview participation and reported interest are not customers or sales.

## Structured interview evidence protocol

The next customer-discovery round should leave behind evidence that another reviewer can audit, rather than only a summary of impressions. This is a collection protocol, not evidence that interviews have already occurred.

For each interview, retain an anonymised record containing the interview date, broad participant fit with the target-user hypothesis, current routine behaviour, one recent example of routine friction, existing workaround or alternative, the single task they would most want simplified, objections to wearing/loading/cleaning/storing a device, relevant purchasing context, and any reason they would reject the concept. Record contradictory and negative responses with the same prominence as positive responses.

Keep solution reactions separate from behaviour evidence. A statement that the concept sounds useful is weaker than a concrete account of a repeated problem, an existing workaround, or a purchase already made to solve it. Do not convert stated interest into demand, willingness to pay, conversion or customer counts.

After a consistent set of interviews exists, summarise patterns only where the underlying records support them. The first-use-case decision should identify which evidence supports the choice, which evidence argues against it, what remains uncertain, and why the selected next physical test is proportionate to the customer evidence available.

## How this affects development

The broader vision is automation across a facial routine. The immediate learning objective is to test a clearly defined part of that experience and use the results to decide what the first product should be. A focused experiment does not validate the complete system.

The existing [product concept](PRODUCT_CONCEPT.md) contains wider whole-routine requirements. Narrowing an initial experiment does not silently remove those requirements or change a completion claim. Any selected product-scope change must be reconciled through [change control](CORE_SKETCH_CHANGE_CONTROL.md) and the relevant engineering authority.

Customer feedback cannot establish physical safety or performance, and passing engineering checks cannot establish customer value. Both lines of evidence are needed before committing to a product or making a readiness claim.

## Decision gates before broadening scope

The next stage should reduce uncertainty before adding product breadth. These are decision gates, not claims that the evidence already exists.

| Gate | Evidence needed | Decision it should inform |
| --- | --- | --- |
| Customer problem | Structured interviews show a recurring routine task that people already experience as sufficiently inconvenient or time-consuming to investigate further. | Select or reject a first use case rather than defaulting to the full routine vision. |
| Net convenience | A focused workflow prototype and customer research show that fitting, loading, cleaning and maintenance do not obviously erase the time or effort saved. | Continue, simplify the workflow, or stop pursuing that use case. |
| Physical feasibility | Focused fit work, fluid-delivery testing and hygiene investigation produce measurements strong enough to replace key digital assumptions. | Decide whether the selected use case deserves deeper hardware development. |
| Commercial plausibility | Initial manufacturing-cost modelling and customer pricing research overlap enough to justify more detailed costing. | Continue, reduce product scope, or reconsider the commercial model. |
| Broader product scope | Customer, physical and cost evidence support adding another routine function without undermining the first use case. | Expand the wearable-and-dock vision only when evidence supports the added complexity. |

A negative result is useful evidence. The purpose of these gates is to prevent repository activity, feature count or digital engineering progress from becoming a substitute for evidence that a product should be built.
