# CS-018 projected-shadow fail-closed patch proposal (14 October 2026)

**Status: REVIEW NEEDED — not implemented in released source.** Owner: Lane 1 Facial Delivery. Baseline main `faae3cec8b80d201c3b7f82c2f29d4bb766cad09`. Canonical CS-018 PR #157 head `c05c9b4146aeb71e213845c6c914748db913dcb2` does not modify this module.

## Finding

`src/masck_one/facial_interface_occlusion.py::rectangle_clip` currently accepts invalid rectangle bounds without a deterministic rejection. Inverted extents, NaN/Inf, and degenerate projected triangles may yield zero/NaN overlap, which the `map_rectangle` filter (`area>1e-9`) can silently discard. A malformed shadow must not masquerade as a clear required skin region.

## Bounded implementation

1. Validate `bounds` is exactly four finite, non-boolean real values in `(xmin,xmax,ymin,ymax)` order, with `xmin<xmax` and `ymin<ymax`. Reject otherwise with `FacialInterfaceError`.
2. Validate exactly three 2D finite real vertices; reject NaN, infinity, booleans, malformed tuples and triangles with projected area <= 1e-12 mm².
3. Preserve existing analytic convex clipping. Compute overlap with numerically stable summation and reject any nonfinite area or result larger than either the source triangle or rectangle area beyond a documented tolerance.
4. Keep projection semantics `UNRESOLVED`: neither a positive projected occupancy nor a zero area proves real contact or film coverage. No engineering authority values change.
5. Add parametrized tests in `tests/test_facial_interface_bench.py` covering inverted/zero bounds, NaN/Inf, bool, malformed/degenerate vertices, winding reversal, inside/outside, and partial clipping.

## Evidence

18 isolated pytest cases passed for a locally constructed candidate implementation. **This is not repo CI and not validation of the current source.** Existing-file GitHub updates and issue comments were blocked by connected-tool safety checks. No source change, PR, merge or qualified exact-head CI was completed.

## Next steps

Implement the bounded source/test patch on this isolated branch when authorized write access succeeds, then run focused `pytest tests/test_facial_interface_bench.py`, relevant facial-interface preflight, and exact-head GitHub CI. Ask the existing CS-018 owner to review before merging. All physical cleansing, carryover, film retention, release and human-fit claims remain unvalidated.
