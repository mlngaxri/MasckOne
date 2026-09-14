# Engineering quickstart

[Project overview](../README.md) · [Documentation index](README.md)

Run these commands from the repository root in an isolated Python 3.13 environment. The package and version constraints in [pyproject.toml](../pyproject.toml) are controlling. Record the checkout commit when comparing results; outputs from different branches are not interchangeable.

## Engineering authority

The primary machine-readable source is:

```text
config/masck_one_authority.yaml
```

Its schema is:

```text
schemas/masck_one_authority.schema.json
```

The repository also contains a separate brand and product-identity contract. Brand intent does not override engineering authority or validation state.

Key principles include:

- one controlled source for engineering parameters
- reproducible CAD generation from source
- explicit separation between manufactured material and reference geometry
- protected anatomy treated as a hard design constraint
- validation-gated requirements remain open until evidence closes them
- generated STEP files are outputs, not the source of engineering truth
- source movement and stale provenance fail closed where relevant

## Key technical areas

The codebase covers a broader system than a conventional CAD repository. Representative modules include:

- `spatial.py`: canonical coordinates, points, vectors and rigid transforms
- `anatomy.py`: semantic facial landmarks and references
- `protected_volumes.py`: eye, mouth and airway exclusion geometry
- `worn_pose.py`: misregistration and worn-pose screening
- `coverage.py`: treatment-region and protected-area accounting
- `interface_topology.py`: compliant facial-interface topology
- `nasal_subsystem.py`: dedicated nasal functional partition
- `contact_simulation.py`: evidence-gated contact-analysis framework
- `structural_frame.py`: structural datum and subsystem reservation architecture
- `actuator_frames.py` and related modules: four-zone actuation references
- `water_reservoir.py`, `cleanser_storage.py` and distribution modules: fresh-fluid architecture
- `waste_acquisition.py`, `waste_pump_architecture.py`, `waste_cartridge.py` and `waste_routes.py`: mixed-waste architecture
- `component_registry.py`: canonical component and interface identity
- `export.py`, `step_integrity.py` and `release_package.py`: deterministic release and STEP verification

See [`docs/REPOSITORY_STRUCTURE.md`](REPOSITORY_STRUCTURE.md) for the broader source hierarchy.

## Toolchain

The currently controlled Python engineering environment uses:

- Python 3.13.x
- CadQuery 2.8.0
- jsonschema 4.26.0
- PyYAML 6.0.3
- pytest 9.0.2

Install the project in an isolated environment:

```bash
python -m pip install -e ".[dev]"
```

## Validation and tests

Validate the engineering authority:

```bash
python -m masck_one.authority
```

Run repository preflight:

```bash
python -m masck_one.preflight
```

Run the complete test suite:

```bash
python -m compileall -q src tests
python -m pytest
```

Generate the current deterministic CAD baseline:

```bash
python -m masck_one.cli --output generated
```

The release build produces STEP files and structured manifests used to verify source identity, geometry integrity and development status.


## Reading a successful run

A passing test or generated STEP file establishes only the software or geometry property being checked. It does not establish physical fit, comfort, leakage, cleansing efficacy or human-use suitability. See the [evidence guide](EVIDENCE_GUIDE.md).

The [engineering CI workflow](../.github/workflows/ci.yml) contains the complete qualified preflight, test, CAD and release-package sequence. The commands above are the entry points, not a replacement for those release gates. Generating into `generated/` may change tracked outputs; use a separate clean checkout when inspecting the project.
