"""Commit SHAs pinned in tracked source or documentation must be verifiable.

A pinned *commit* is a provenance claim: "this artifact corresponds to that
commit". The claim is only useful if a normal clone can resolve it. Two things
break that, and both occur here:

  * the pin is a pull-request head that was later force-pushed, so it is no
    longer an ancestor of ``main``;
  * the pin only ever existed under ``refs/pull/*``, which clones do not fetch.

In both cases the remedy is identical: **pin a merged commit, not a branch
head.** A merge commit on ``main`` is immutable and reachable from every clone;
a branch head is neither.

Scope
-----
This gate judges *commits only*. Most 40-hex literals in this repository are git
**blob** hashes -- content pins used by, for example,
``component_registry.SOURCE_GIT_BLOBS`` to fail closed when a bound source file
moves. Those are a different and entirely legitimate mechanism: a blob has no
ancestry, and its correctness is enforced by the code that compares it. They are
classified and excluded rather than judged.

Objects absent from the object database cannot be classified at all -- an
unresolvable hash may be a stale blob or a collected commit -- so they are
reported separately and never counted as commit debt.
"""

from __future__ import annotations

from pathlib import Path
import re
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]

_SHA40 = re.compile(r"\b[0-9a-f]{40}\b")

_SCAN_GLOBS = ("*.md", "docs/*.md", "src/masck_one/*.py", "tests/*.py", "config/*.yaml")

# Deliberate non-hash 40-hex literals (hostile-test fixtures and the like).
_ALLOWED_NON_COMMITS = frozenset({"a" * 40, "0" * 40, "f" * 40, "1" * 40})

# Commit pins that are real commits but are NOT ancestors of main: each is an
# open pull-request head that was force-pushed after being pinned. Every one is
# the same defect as the pull-request state formerly compiled into
# src/masck_one/integration_contract.py, and the same fix applies -- pin the
# merge commit, not the branch head.
#
# Retiring an entry belongs to the lane that owns the file (see
# src/masck_one/integration_contract.py). This set is a RATCHET: it may only
# shrink. New bad pins fail; entries that reach the RELEASE LINE must be deleted.
#
# "Release line", not "HEAD", and the distinction is load-bearing. Reachability
# from HEAD is branch-relative, so the same frozenset gave opposite verdicts on
# two branches at once: three of these commits are ancestors of the Cell 6 frame
# branch but of no released commit. Judged against HEAD, keeping them failed the
# self-clean check on that branch and removing them failed the orphan check on
# main -- a deadlock no value of this set could satisfy.
#
# Landing on a feature branch does not retire provenance debt anyway. That branch
# can still be force-pushed or abandoned, which is the exact failure this gate
# exists to catch. Debt is retired by reaching main, and by nothing else.
_KNOWN_UNVERIFIABLE_COMMIT_PINS = frozenset({
    "0b5a619c6cea344038b0e8b8cc10a50e3d193390",  # src/masck_one/mechanical_interface_graph.py
    "34273de3bd86294080e51873c212e988b4a966f4",  # src/masck_one/mechanical_interface_graph.py
    "37e03df4b6abbd222422c8bfd4e70b03a4e5ae07",  # src/masck_one/mechanical_interface_graph.py
    "43c3866eea56801696068ad4e417d5b21498682d",  # src/masck_one/thermal_reset_hardware.py
    "630cc19497661ae834032eb8ea06e28dfd6100b7",  # src/masck_one/mechanical_interface_graph.py
    "ca128295794ff51ed96e7a840428de55ea36de6b",  # src/masck_one/mechanical_interface_graph.py
    "ce1a175a79f87da65d88a40eca146f3dc5419528",  # src/masck_one/mechanical_interface_graph.py
    "da14a860e69c48191fc8e8204d895b2b9dd5f469",  # docs/PRODUCTION_CLOSURE_2026-09-07.md
    "fb586cc1ea1cde92526417593f9e5aa990d2ae4f",  # src/masck_one/mechanical_interface_graph.py
})


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False
    )


def _is_git_worktree() -> bool:
    return _git("rev-parse", "--git-dir").returncode == 0


def _is_shallow() -> bool:
    return _git("rev-parse", "--is-shallow-repository").stdout.strip() == "true"


def _tracked_files() -> list[Path]:
    result = _git("ls-files", *_SCAN_GLOBS)
    if result.returncode != 0:
        return []
    return [ROOT / line for line in result.stdout.splitlines() if line]


def _pinned_hashes() -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for path in _tracked_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for sha in set(_SHA40.findall(text)):
            if sha in _ALLOWED_NON_COMMITS:
                continue
            found.setdefault(sha, []).append(str(path.relative_to(ROOT)))
    return found


def _release_line() -> str:
    """The released line to judge debt against; HEAD only if nothing else resolves.

    Falling back to HEAD reproduces the historical behaviour exactly, so a clone
    without a main ref is no worse off than before.
    """

    for ref in ("refs/remotes/origin/main", "refs/heads/main", "origin/main", "main"):
        if _git("rev-parse", "--verify", "--quiet", ref + "^{commit}").returncode == 0:
            return ref
    return "HEAD"


def _reachable_from_release(sha: str) -> bool:
    return _git("merge-base", "--is-ancestor", sha, _release_line()).returncode == 0


def _object_kind(sha: str) -> str:
    """'commit', 'blob', 'tree', 'tag', or 'absent'."""

    return _git("cat-file", "-t", sha).stdout.strip() or "absent"


def _classify() -> dict[str, list[tuple[str, list[str]]]]:
    buckets: dict[str, list[tuple[str, list[str]]]] = {
        "commit_ok": [], "commit_orphaned": [], "blob": [], "absent": [], "other": []
    }
    for sha, files in sorted(_pinned_hashes().items()):
        kind = _object_kind(sha)
        if kind == "commit":
            reachable = _git("merge-base", "--is-ancestor", sha, "HEAD").returncode == 0
            buckets["commit_ok" if reachable else "commit_orphaned"].append((sha, files))
        elif kind == "blob":
            buckets["blob"].append((sha, files))
        elif kind == "absent":
            buckets["absent"].append((sha, files))
        else:
            buckets["other"].append((sha, files))
    return buckets


requires_git = pytest.mark.skipif(not _is_git_worktree(), reason="not a git worktree")
requires_full_history = pytest.mark.skipif(
    _is_shallow(), reason="shallow clone cannot resolve object reachability"
)


@requires_git
@requires_full_history
def test_no_new_orphaned_commit_pins() -> None:
    orphaned = _classify()["commit_orphaned"]
    unexpected = [
        f"{sha} referenced by {', '.join(sorted(files))}"
        for sha, files in orphaned
        if sha not in _KNOWN_UNVERIFIABLE_COMMIT_PINS
    ]
    assert not unexpected, (
        "these pinned commits are not ancestors of HEAD:\n  "
        + "\n  ".join(unexpected)
        + "\n\nPin a merged commit, not a branch head."
    )


@requires_git
@requires_full_history
def test_debt_set_self_cleans() -> None:
    """An entry that reached the release line must be deleted from the debt set.

    Otherwise the ratchet quietly stops ratcheting: retired debt lingers and
    keeps granting an exemption nobody needs.
    """

    now_reachable = [
        sha
        for sha in sorted(_KNOWN_UNVERIFIABLE_COMMIT_PINS)
        if _object_kind(sha) == "commit" and _reachable_from_release(sha)
    ]
    assert not now_reachable, (
        "these pins are now reachable and must be removed from "
        "_KNOWN_UNVERIFIABLE_COMMIT_PINS:\n  " + "\n  ".join(now_reachable)
    )


@requires_git
@requires_full_history
def test_commit_pin_debt_does_not_grow() -> None:
    """Nine orphaned commit pins was the state when this gate was introduced."""

    assert len(_KNOWN_UNVERIFIABLE_COMMIT_PINS) <= 9, (
        f"{len(_KNOWN_UNVERIFIABLE_COMMIT_PINS)} orphaned commit pins; "
        "the ratchet only shrinks"
    )


@requires_git
@requires_full_history
def test_unresolvable_pins_do_not_grow() -> None:
    """A hash that resolves to nothing must not be able to appear silently.

    Restricting the reachability rule to objects that are actually commits fixed
    a 26/39 false-positive rate against blob content pins, but it opened a hole:
    a fabricated or mistyped hash resolves to nothing, so it is neither a commit
    nor a blob and nothing judged it.

    Absence is genuinely ambiguous -- it may be a stale blob from an earlier
    version of a bound file, or a PR head a clone never fetched -- so these are
    not failed outright. But the count is pinned, so a new one cannot slip in
    unnoticed.
    """

    absent = _classify()["absent"]
    assert len(absent) <= 4, (
        "unresolvable pinned hashes increased:\n  "
        + "\n  ".join(
            f"{sha} referenced by {', '.join(sorted(files))}" for sha, files in absent
        )
        + "\n\nA hash that resolves to no git object is not provenance."
    )


@requires_git
@requires_full_history
def test_blob_pins_are_classified_not_judged() -> None:
    """Content pins are a legitimate, different mechanism.

    component_registry.SOURCE_GIT_BLOBS fails the build closed when a bound
    source file moves. Blobs have no ancestry, so the reachability rule does not
    apply to them and must not be silently applied.
    """

    buckets = _classify()
    assert buckets["blob"], "expected blob content pins; scan may be broken"
    assert not (
        {sha for sha, _ in buckets["blob"]} & _KNOWN_UNVERIFIABLE_COMMIT_PINS
    ), "a blob hash leaked into the commit-pin debt set"


@requires_git
@requires_full_history
def test_scan_finds_pins_across_source_and_docs() -> None:
    """Guard against the scan silently matching nothing."""

    buckets = _classify()
    total = sum(len(v) for v in buckets.values())
    assert total >= 20, f"pinned-hash scan found only {total} references"
    assert buckets["commit_ok"], "no verifiable commit pins found at all"


@requires_git
@requires_full_history
def test_release_line_prefers_main_over_head() -> None:
    """The line debt is judged against must be main whenever main resolves.

    HEAD is the fallback of last resort, and only because falling back to it
    reproduces the historical behaviour exactly rather than inventing a new one.
    """

    has_main = any(
        _git("rev-parse", "--verify", "--quiet", ref + "^{commit}").returncode == 0
        for ref in ("refs/remotes/origin/main", "refs/heads/main")
    )
    assert (_release_line() != "HEAD") == has_main


@requires_git
@requires_full_history
def test_feature_branch_reachability_does_not_retire_debt() -> None:
    """Debt retires by reaching main, not by appearing on somebody's branch.

    This is the regression for the defect that motivated ``_release_line``. When
    the self-clean check judged reachability from HEAD, a commit that existed
    only on an unmerged branch retired its own debt the moment CI ran on that
    branch -- while the orphan check, running on main, still demanded the
    exemption. The two gates contradicted each other and no value of the debt set
    could satisfy both.

    ``_reachable_from_release`` is compared against a direct query on main rather
    than against itself, so a release line that silently degrades to HEAD is
    caught by the disagreement instead of passing by construction.
    """

    refs = _git("for-each-ref", "--format=%(refname)", "refs/remotes", "refs/heads")
    checked = 0
    for ref in refs.stdout.split():
        if ref.endswith(("/main", "/HEAD")):
            continue
        tip = _git("rev-parse", "--verify", "--quiet", ref + "^{commit}").stdout.strip()
        if not tip:
            continue
        oracle = _git(
            "merge-base", "--is-ancestor", tip, "refs/remotes/origin/main"
        ).returncode == 0
        assert _reachable_from_release(tip) == oracle, (
            f"{ref} ({tip}) is judged released={_reachable_from_release(tip)} but "
            f"main says {oracle}; the release line is not main"
        )
        checked += 1
    # A clone with no branches beyond main cannot exercise the rule, and saying so
    # is more honest than a pass that examined nothing.
    assert checked or not _git(
        "rev-parse", "--verify", "--quiet", "refs/remotes/origin/main^{commit}"
    ).returncode == 0
