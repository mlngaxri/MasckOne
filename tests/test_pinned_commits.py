"""Every commit SHA pinned in tracked source or documentation must be verifiable.

A pinned SHA is a provenance claim: "this artifact corresponds to that commit".
The claim is only useful if someone with a normal clone can resolve it. Three
things break that, and all three are common here:

  * the commit was garbage-collected after its branch was rewritten;
  * the commit is a pull-request head that was later force-pushed;
  * the commit only ever existed under ``refs/pull/*``, which clones do not fetch.

In all three cases the remedy is identical: **pin a merged commit, not a branch
head.** A merge commit on ``main`` is immutable and reachable from every clone.
A branch head is neither.

This gate therefore requires that any 40-hex identifier presented as a commit is
an ancestor of ``HEAD``. It is a ratchet, not a cliff: the pins that already
fail are enumerated in ``_KNOWN_UNVERIFIABLE_PINS`` so the debt is visible, and
the gate fails only on new ones.
"""

from __future__ import annotations

from pathlib import Path
import re
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]

_SHA40 = re.compile(r"\b[0-9a-f]{40}\b")

# Scanned locations. Generated output and vendored assets are excluded.
_SCAN_GLOBS = ("*.md", "docs/*.md", "src/masck_one/*.py", "tests/*.py", "config/*.yaml")

# Deliberate non-commit 40-hex literals (hostile-test fixtures and the like).
_ALLOWED_NON_COMMITS = frozenset({
    "a" * 40,
    "0" * 40,
    "f" * 40,
})

# Known unverifiable pins, enumerated rather than hidden.
#
# Every entry below is a commit that a released source file or document presents
# as provenance but that cannot be resolved from this history: it was either
# garbage-collected after its branch was rewritten, or it is a pull-request head
# that was force-pushed and is not an ancestor of main. The claim each one makes
# is therefore unverifiable today.
#
# Measured at the time of writing: 30 of these are absent from the object
# database even after fetching every remote branch; 9 resolve to open
# pull-request heads that are not ancestors of main.
#
# Root cause is uniform: these pin *mutable branch heads* instead of merged
# commits. The fix in each case is the one applied to
# src/masck_one/integration_contract.py -- stop compiling live PR/branch state
# into source, and pin only commits that are already merged.
#
# This set is a RATCHET. It may only ever shrink:
#   * any NEW unverifiable pin fails test_no_new_unverifiable_pins;
#   * any entry here that becomes reachable fails test_debt_set_self_cleans and
#     must be deleted from this list.
# Owning lanes (see src/masck_one/integration_contract.py) are responsible for
# retiring their own entries.
_KNOWN_UNVERIFIABLE_PINS = frozenset({
    "0b5a619c6cea344038b0e8b8cc10a50e3d193390",  # src/masck_one/mechanical_interface_graph.py
    "0ea2ada736825fe1a0e06491d16690ae98cfccde",  # src/masck_one/mechanical_interface_graph.py
    "11d90a75eb108c53f5a1621abdace7271bf5cac5",  # src/masck_one/mechanical_interface_graph.py
    "2608dda483b995539de422290371c219668a1527",  # docs/PRODUCTION_CLOSURE_2026-09-07.md
    "34273de3bd86294080e51873c212e988b4a966f4",  # src/masck_one/mechanical_interface_graph.py
    "34a49eed2c521d55e48ac187c2dd33dc9e22a3e3",  # src/masck_one/waste_cartridge_dfm.py
    "37e03df4b6abbd222422c8bfd4e70b03a4e5ae07",  # src/masck_one/mechanical_interface_graph.py
    "38b7c932f71a8675d45d098ac65154f98ff8bbb5",  # src/masck_one/component_registry.py
    "40cb6fb4c3efbfcf25ed0b7d7a75a4269d90a1b4",  # src/masck_one/component_registry.py
    "43587520a8c6cdc9ca8cfe362d2aac9589364fdc",  # src/masck_one/waste_cartridge_dfm.py
    "43c3866eea56801696068ad4e417d5b21498682d",  # src/masck_one/thermal_reset_hardware.py
    "4c2013f994bdc9e084fe227eb5e166f973500ebb",  # src/masck_one/component_registry.py
    "4c58b0dc81fd2e95a6f1405ea5eeb1641ba8a3c8",  # src/masck_one/mechanical_interface_graph.py
    "5e087ca8b05da8352ad4800b2ef8280ea8ddcf29",  # src/masck_one/component_registry.py
    "630cc19497661ae834032eb8ea06e28dfd6100b7",  # src/masck_one/mechanical_interface_graph.py
    "6aa79d9a613e278f32da85b4654c0e35cc09b7ca",  # src/masck_one/component_registry.py
    "6c14a37d07855550f0bd502e8308ed46682bc19c",  # src/masck_one/component_registry.py
    "7108fcfbe2baeaa9a343199a6817122ac2aea7ab",  # src/masck_one/component_registry.py
    "8f2a6c784b51734aba4d1f3809015707fc328405",  # src/masck_one/component_registry.py
    "90d20231710a24bbf02ba0c9ae52ef8b37f0ce73",  # src/masck_one/mechanical_interface_graph.py
    "9647405b36642105c929a3fdd0617d03bfe68c98",  # src/masck_one/mechanical_interface_graph.py
    "9c613f40ed1b8cb43c3a40bb945d53084a71d121",  # src/masck_one/mechanical_interface_graph.py
    "9dc0fe8a0ed92083c68406da3993e57e767e2483",  # src/masck_one/component_registry.py
    "9e0b7a7c5d05106b2782a7346873af9a688668ee",  # docs/cell4_realized_waste_backbone.md
    "9e7fa6c71ac28cc45ebb502444bf6c0ea49f7894",  # src/masck_one/component_registry.py
    "a2a3d659a380ccba1ac20621e56be9a2aa6bc104",  # docs/cell4_realized_waste_backbone.md
    "ace02ee529070465b11832f475771125636312cb",  # src/masck_one/component_registry.py
    "b497e9154067cef9ee24da4d421ea6c7861c348e",  # src/masck_one/mechanical_interface_graph.py
    "bda5ba87d232c0e6a22e200975a80414a10c9a83",  # src/masck_one/component_registry.py
    "c161f99ddd3473f3b9dde30ec73397a72915191a",  # src/masck_one/waste_cartridge_dfm.py
    "ca128295794ff51ed96e7a840428de55ea36de6b",  # src/masck_one/mechanical_interface_graph.py
    "ce1a175a79f87da65d88a40eca146f3dc5419528",  # src/masck_one/mechanical_interface_graph.py
    "d2dd8b47bb6a2aa1edf57ac0632778228add7997",  # src/masck_one/component_registry.py
    "d56160304190c030e3bc389803eaa456aaab5af0",  # src/masck_one/component_registry.py
    "d68a109c93532bfa424a574fdbd899230ae20d0b",  # src/masck_one/mechanical_interface_graph.py
    "da14a860e69c48191fc8e8204d895b2b9dd5f469",  # docs/PRODUCTION_CLOSURE_2026-09-07.md
    "e44c8ca12d7b163a5a3fb54fbce7ca2c16d0fc5c",  # src/masck_one/mechanical_interface_graph.py
    "f9788cce30c14600c8a624509153596e46c1e478",  # src/masck_one/component_registry.py
    "fb586cc1ea1cde92526417593f9e5aa990d2ae4f",  # src/masck_one/mechanical_interface_graph.py
})


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False
    )


def _is_git_worktree() -> bool:
    return _git("rev-parse", "--git-dir").returncode == 0


def _tracked_files() -> list[Path]:
    result = _git("ls-files", *_SCAN_GLOBS)
    if result.returncode != 0:
        return []
    return [ROOT / line for line in result.stdout.splitlines() if line]


def _pinned_shas() -> dict[str, list[str]]:
    """Map each pinned SHA to the files that reference it."""

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


@pytest.mark.skipif(not _is_git_worktree(), reason="not a git worktree")
def test_no_new_unverifiable_pins() -> None:
    pins = _pinned_shas()
    if not pins:
        pytest.skip("no pinned commit SHAs found")

    # A shallow clone cannot answer reachability; do not fail on it.
    if _git("rev-parse", "--is-shallow-repository").stdout.strip() == "true":
        pytest.skip("shallow clone cannot resolve commit reachability")

    unreachable: list[str] = []
    for sha, files in sorted(pins.items()):
        exists = _git("cat-file", "-e", f"{sha}^{{commit}}").returncode == 0
        ancestor = (
            exists
            and _git("merge-base", "--is-ancestor", sha, "HEAD").returncode == 0
        )
        if not ancestor:
            reason = "object missing" if not exists else "not an ancestor of HEAD"
            unreachable.append(
                (sha, f"{sha} ({reason}) referenced by {', '.join(sorted(files))}")
            )

    unexpected = [row for sha, row in unreachable if sha not in _KNOWN_UNVERIFIABLE_PINS]
    assert not unexpected, (
        "new pinned commit SHAs are not verifiable from this history:\n  "
        + "\n  ".join(unexpected)
        + "\n\nPin a merged commit, not a branch head. See "
          "_KNOWN_UNVERIFIABLE_PINS in this file."
    )


@pytest.mark.skipif(not _is_git_worktree(), reason="not a git worktree")
def test_scan_actually_finds_the_known_release_pins() -> None:
    """Guard against the scan silently matching nothing."""

    pins = _pinned_shas()
    assert len(pins) >= 3, f"pinned-commit scan found only {len(pins)} references"


@pytest.mark.skipif(not _is_git_worktree(), reason="not a git worktree")
def test_debt_set_self_cleans() -> None:
    """An entry that became reachable must be removed from the debt set.

    Without this the ratchet would silently stop ratcheting: retired debt would
    linger and keep granting an exemption nobody needs any more.
    """

    if _git("rev-parse", "--is-shallow-repository").stdout.strip() == "true":
        pytest.skip("shallow clone cannot resolve commit reachability")

    now_reachable = [
        sha
        for sha in sorted(_KNOWN_UNVERIFIABLE_PINS)
        if _git("cat-file", "-e", f"{sha}^{{commit}}").returncode == 0
        and _git("merge-base", "--is-ancestor", sha, "HEAD").returncode == 0
    ]
    assert not now_reachable, (
        "these pins are now reachable and must be deleted from "
        "_KNOWN_UNVERIFIABLE_PINS:\n  " + "\n  ".join(now_reachable)
    )


@pytest.mark.skipif(not _is_git_worktree(), reason="not a git worktree")
def test_debt_set_is_not_silently_growing() -> None:
    """Hard cap on outstanding unverifiable provenance.

    39 entries was the state when this gate was introduced. The number may fall;
    raising it means a lane pinned another branch head and should be challenged
    in review rather than absorbed.
    """

    assert len(_KNOWN_UNVERIFIABLE_PINS) <= 39, (
        f"{len(_KNOWN_UNVERIFIABLE_PINS)} unverifiable pins; the ratchet only shrinks"
    )
