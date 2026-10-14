# CS-018 shadow projection validation

Current development-plane clipping accepts inverted and non-finite rectangle bounds without an explicit error. Such input may produce an empty occupancy result rather than an unresolved blocker. This file records the proposed fail-closed regression target. No physical validation is implied.
