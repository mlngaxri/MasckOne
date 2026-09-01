# Cell 2 canonical visual source boundary

This module removes test-fixture construction from the future Web/App consumer path without inventing provenance.

`build_canonical_visual_system()` owns only Cell-2 presentation semantics: typography roles and light, dark and high-contrast appearance roles. The resulting `AdaptiveVisualSystem` remains presentation-only and cannot become geometry authority, CMF approval, engineering evidence or physical evidence.

The builder requires two inputs that must agree exactly:

1. an invariant-valid `UnifiedDesignLanguage` object;
2. the expected SHA-256 of that design-language manifest.

The second input is deliberately mandatory, but equality is not authentication. Production code must obtain the expected digest from a separately authenticated release artifact. This module does not infer release state from a syntactically valid hash, a Git commit, a test fixture or a caller label. A mismatch fails closed. Post-construction corruption of the supplied language is revalidated before use.

`build_canonical_digital_exports()` emits Web then App exports from the same canonical visual system and verifies that both targets carry the same `visual_system_sha256`, `payload_sha256` and semantic payload. Their target-specific manifest hashes remain distinct.

This closes the Cell-2 construction side of the dual-hash boundary. It does not create the missing authenticated upstream design-language artifact. A concrete production export must wait for an actual released engineering presentation source and a release mechanism that verifies artifact bytes and source provenance. No placeholder SHA is permitted.
