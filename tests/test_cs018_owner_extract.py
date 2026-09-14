"""Source provenance and evidence classification for isolated owner extraction."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

TOOL = Path(__file__).resolve().parents[1] / 'tools/cs018_owner_extract.py'
spec = importlib.util.spec_from_file_location('owner_extract_under_test', TOOL)
extractor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extractor)


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.PIPE).decode().strip()


@pytest.fixture
def source(tmp_path):
    root = tmp_path / 'source'
    root.mkdir()
    git(root, 'init', '-q')
    git(root, 'config', 'user.name', 'Synthetic Test')
    git(root, 'config', 'user.email', 'synthetic@example.invalid')
    package = root / 'src/masck_one'
    package.mkdir(parents=True)
    (package / '__init__.py').write_text('')
    module = package / 'thermal_reset_hardware.py'
    module.write_text("import cadquery as cq\ndef build_thermal_reset_hardware():\n"
                      "    return ({'coupon':cq.Workplane('XY').box(2,2,2)},\n"
                      "            {'sweep':cq.Workplane('XY').box(3,3,3)},\n"
                      "            {'scope':'SYNTHETIC_OFF_FACE'})\n")
    git(root, 'add', '.')
    git(root, 'commit', '-qm', 'synthetic owner')
    return root, git(root, 'rev-parse', 'HEAD'), module


def test_clean_checkout_and_loaded_bytes_bind_to_commit(source):
    root, head, module = source
    assert extractor.verify_checkout(root, head) == git(root, 'rev-parse', 'HEAD^{tree}')
    rows = extractor.verify_loaded_sources(root, head,
        {'masck_one.thermal_reset_hardware': SimpleNamespace(__file__=str(module))})
    row = rows[module.relative_to(root).as_posix()]
    assert row['head'] == head and len(row['sha256']) == 64
    assert row['git_blob'] == git(root, 'rev-parse', head + ':' + module.relative_to(root).as_posix())


@pytest.mark.parametrize('head', ['main', 'abc123', 'f' * 40, None])
def test_head_alias_or_wrong_commit_cannot_label_output(source, head):
    root, _, _ = source
    with pytest.raises(ValueError):
        extractor.verify_checkout(root, head)


def test_producer_commit_movement_requires_a_new_requested_head(source):
    root, head, _ = source
    git(root, 'commit', '--allow-empty', '-qm', 'synthetic source moved')
    with pytest.raises(ValueError, match='HEAD differs'):
        extractor.verify_checkout(root, head)


@pytest.mark.parametrize('staged', [False, True])
def test_dirty_tracked_inputs_are_rejected(source, staged):
    root, head, module = source
    module.write_text(module.read_text() + '# changed\n')
    if staged:
        git(root, 'add', '.')
    with pytest.raises(ValueError, match='dirty'):
        extractor.verify_checkout(root, head)


@pytest.mark.parametrize('kind', ['foreign', 'untracked', 'modified'])
def test_import_hashing_does_not_certify_unbound_code(source, tmp_path, kind):
    root, head, module = source
    if kind == 'foreign':
        module = tmp_path / 'foreign.py'
    elif kind == 'untracked':
        module = module.parent / 'untracked.py'
    module.write_text('# unbound code\n')
    with pytest.raises(ValueError, match='mixed owner|not tracked|bytes differ'):
        extractor.verify_loaded_sources(root, head,
            {'masck_one.thermal_reset_hardware': SimpleNamespace(__file__=str(module))})


def test_existing_output_is_preserved(source, tmp_path):
    root, head, _ = source
    output = tmp_path / 'old_output'
    output.mkdir()
    original = output / 'previous.step'
    original.write_text('previous evidence')
    with pytest.raises(ValueError, match='fresh output directory'):
        extractor.extract('thermal', root, output, head)
    assert original.read_text() == 'previous evidence'


@pytest.mark.parametrize('case', ['thermal', 'unsupported', 'dirty', 'failed_producer'])
def test_isolated_cli_preserves_unknowns_and_failure_codes(source, tmp_path, case):
    root, head, module = source
    if case == 'dirty':
        module.write_text(module.read_text() + '# changed\n')
    if case == 'failed_producer':
        module.write_text("def build_thermal_reset_hardware():\n    raise ValueError('synthetic producer gate')\n")
        git(root, 'add', '.')
        git(root, 'commit', '-qm', 'synthetic failure')
        head = git(root, 'rev-parse', 'HEAD')
    output = tmp_path / 'output'
    owner = 'undeclared' if case == 'unsupported' else 'thermal'
    env = dict(os.environ, PYTHONPATH=str(root / 'src'))
    run = subprocess.run([sys.executable, str(TOOL), owner, str(root), str(output), head],
                         env=env, capture_output=True, text=True)
    result = json.loads((output / 'owner_geometry.json').read_text())
    assert run.returncode == (0 if case == 'thermal' else 2), run.stderr
    assert result['physical_result'] is None and result['human_use_eligible'] is False
    assert result['capability_status'] == 'UNRESOLVED_OWNER_CAPABILITY'
    if case == 'thermal':
        assert result['source_binding_status'] == 'EXACT_CHECKOUT_AND_LOADED_BLOBS_VERIFIED'
        assert len(result['participants']) == 2
        assert {r['classification'] for r in result['participants']} == {'REFERENCE', 'OWNER_MATERIAL_CANDIDATE'}
        assert all(r['registered_facial_contact'] is None for r in result['participants'])
    else:
        expected = {'unsupported': 'UNRESOLVED_OWNER_CAPABILITY', 'dirty': 'SOURCE_BINDING_FAILED',
                    'failed_producer': 'PRODUCER_FAILED_NO_CLEARANCE_INFERENCE'}
        assert result['status'] == expected[case]
        assert result['participants'] == []
