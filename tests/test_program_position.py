"""Keep every statement of "where the program is" bound to one source.

Before this gate the repository asserted three different answers at once:
README.md said Phase 2 / Iteration 11, docs/DEVELOPMENT_ROADMAP.md marked 28
iterations COMPLETE, and build_report.json shipped development_phase 3 /
iteration 15. Prose drifts silently; a test does not.

config/masck_one_authority.yaml is the single source. Everything else is
checked against it.
"""

from __future__ import annotations

from pathlib import Path
import re

import pytest

from masck_one.authority import load_authority

ROOT = Path(__file__).resolve().parents[1]
ROADMAP = ROOT / "docs" / "DEVELOPMENT_ROADMAP.md"
README = ROOT / "README.md"

_PHASE_HEADING = re.compile(r"^##\s+Phase\s+(\d+)\b", re.MULTILINE)
_ITERATION_LINE = re.compile(r"^(\d+)\.\s+(.*)$", re.MULTILINE)


def _roadmap_phase_of_iteration() -> dict[int, int]:
    """Map each numbered roadmap iteration to the phase heading above it."""

    text = ROADMAP.read_text(encoding="utf-8")
    boundaries = [(m.start(), int(m.group(1))) for m in _PHASE_HEADING.finditer(text)]
    assert boundaries, "roadmap has no phase headings"

    mapping: dict[int, int] = {}
    for match in _ITERATION_LINE.finditer(text):
        iteration = int(match.group(1))
        phase = next(
            (p for start, p in reversed(boundaries) if start < match.start()), None
        )
        if phase is not None:
            mapping[iteration] = phase
    return mapping


def _roadmap_completed() -> set[int]:
    text = ROADMAP.read_text(encoding="utf-8")
    return {
        int(m.group(1))
        for m in _ITERATION_LINE.finditer(text)
        if "**COMPLETE**" in m.group(2)
    }


@pytest.fixture(scope="module")
def authority():
    return load_authority()


def test_authority_declares_program_position(authority) -> None:
    phase = authority.get("project", "development_phase")
    iteration = authority.get("project", "completed_iteration")
    assert isinstance(phase, int) and phase >= 1
    assert isinstance(iteration, int) and iteration >= 1


def test_roadmap_completion_matches_authority(authority) -> None:
    completed = _roadmap_completed()
    declared = authority.get("project", "completed_iteration")

    assert completed, "roadmap marks no iteration COMPLETE"
    assert max(completed) == declared, (
        f"roadmap's highest COMPLETE iteration is {max(completed)} but "
        f"project.completed_iteration is {declared}"
    )


def test_completed_iterations_are_contiguous() -> None:
    """A gap means an iteration was skipped or a COMPLETE marker was lost."""

    completed = sorted(_roadmap_completed())
    assert completed == list(range(1, max(completed) + 1)), (
        f"non-contiguous COMPLETE iterations: missing "
        f"{sorted(set(range(1, max(completed) + 1)) - set(completed))}"
    )


def test_declared_phase_contains_declared_iteration(authority) -> None:
    mapping = _roadmap_phase_of_iteration()
    iteration = authority.get("project", "completed_iteration")
    declared_phase = authority.get("project", "development_phase")

    assert iteration in mapping, f"iteration {iteration} is not in the roadmap"
    assert mapping[iteration] == declared_phase, (
        f"roadmap places iteration {iteration} in phase {mapping[iteration]} "
        f"but project.development_phase is {declared_phase}"
    )


def test_readme_does_not_contradict_the_authority(authority) -> None:
    """README must not name a stale phase/iteration as the current state."""

    text = README.read_text(encoding="utf-8")
    phase = authority.get("project", "development_phase")
    iteration = authority.get("project", "completed_iteration")

    stated = re.search(
        r"\*\*Phase\s+(\d+):.*?Iteration\s+(\d+)", text, re.DOTALL
    )
    assert stated, "README no longer states a current phase/iteration in bold"
    assert (int(stated.group(1)), int(stated.group(2))) == (phase, iteration), (
        f"README states Phase {stated.group(1)} / Iteration {stated.group(2)} but the "
        f"authority declares Phase {phase} / Iteration {iteration}"
    )
