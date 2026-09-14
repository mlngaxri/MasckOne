# Website development tooling

This directory retains scripts, encoded input assets and trigger files used to construct earlier website iterations. It is development infrastructure, not the product engineering source or a physical validation record.

- The current presentation files live in [website/](../website/).
- Engineering-to-presentation rules are in the [digital product handoff](../DIGITAL_PRODUCT_HANDOFF_README.md).
- Existing [website workflows](../.github/workflows/) still reference scripts and flag files here. Some workflows write generated website changes back to the repository; this directory is not a general-purpose build command for the current site.
- Numbered names identify historical revisions. Retaining them preserves source references and asset provenance; a higher revision number is not evidence of product maturity.

Do not run an old reconstruction script against the current website without reviewing its inputs, expected source and output paths. Removing this directory requires a separate review of workflow dependencies and retained assets.
