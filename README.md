# Blender Asset Pipeline

Blender Asset Pipeline is an installable Blender add-on for validating game-ready
mesh assets and applying a small set of explicitly selected, previewed repairs.
Validation remains read-only. Fixing is a separate opt-in workflow with risk labels,
confirmation, stale-plan protection, undo integration, and automatic revalidation.
Scene-wide batch validation produces deterministic schema-versioned JSON for
artists, technical artists, and future automation.

Version: **0.3.0**

## Current features

- Validate the active object or every selected object from the 3D View sidebar.
- Skip cameras, lights, empties, and other non-mesh objects with a clear warning.
- Check object names, a configurable naming style and optional required prefix.
- Check unapplied location, rotation, and scale with a configurable tolerance.
- Report polygon and triangulated face counts and enforce a configurable triangle
  budget.
- Detect missing material slots, empty slots, and duplicate material assignments.
- Check for a UV map and usable mesh geometry.
- Detect unassigned image texture nodes and missing external texture files when
  Blender can resolve them.
- Classify every result as `PASS`, `WARNING`, or `ERROR`.
- Show a summary and detailed results in the sidebar and write a complete report to
  Blender's system console.
- Batch validate the current scene or every scene in the blend file.
- Deduplicate objects shared by multiple scenes while preserving sorted scene
  memberships in the report.
- Summarize object outcomes, check severities, and aggregate mesh geometry.
- Export the exact latest batch result as deterministic, UTF-8 JSON using report
  schema version `1.0` and an atomic file replacement.
- Generate a fix plan without modifying assets, grouped by object in the sidebar.
- Select fixes individually, select all `SAFE` fixes, or deselect the entire plan.
- Normalize names with the configured convention and collision-safe suffixes.
- Apply location, rotation, and scale independently where object state is safe.
- Remove unused empty material slots and consolidate exact duplicate datablocks
  while preserving polygon material assignments.
- Reject stale plans when relevant object, transform, material, or geometry state
  changes after preview.
- Apply selected fixes as one Blender undo operation and immediately revalidate the
  affected objects.

## Installation

1. Download or clone this repository.
2. Create a ZIP whose top-level folder is `blender_asset_pipeline` (do not ZIP the
   entire repository). From the repository root, for example:

   ```powershell
   Compress-Archive -Path blender_asset_pipeline -DestinationPath blender_asset_pipeline-0.3.0.zip
   ```

3. In Blender, open **Edit > Preferences > Add-ons**, choose **Install...**, select
   the ZIP, and enable **Asset Pipeline: Game Asset Validator & Fixer**.

For development, place or symlink `blender_asset_pipeline/` in Blender's add-ons
directory, then enable the add-on.

The add-on targets Blender 3.6 LTS and newer Blender releases using the traditional
Python add-on packaging format.

## Usage

1. Open the 3D View and press **N** to display its sidebar.
2. Select the **Asset Pipeline** tab.
3. Use **Validate Active Object** or **Validate Selected Objects**.
4. Review the summary and detailed checks in the panel. The same run is printed in
   full to the system console (**Window > Toggle System Console** on Windows, or the
   terminal used to launch Blender on macOS/Linux).
5. Configure the triangle limit, naming convention, optional prefix, and transform
   tolerance in **Edit > Preferences > Add-ons > Asset Pipeline: Game Asset
   Validator & Fixer**.

### Batch validation and JSON reports

The **Batch Validation** subpanel provides two read-only scopes:

- **Validate Current Scene** discovers every object in the active scene.
- **Validate All Scenes** discovers objects across all scenes and validates a
  shared Blender object only once. Its complete sorted scene-membership list is
  retained.

The sidebar shows discovered, validated, and skipped counts; clean, warning-only,
and error-object counts; check totals; aggregate vertices, polygons, and triangles;
the largest mesh; and a capped attention list. A concise bounded summary is also
printed to the system console. Unsupported object types remain visible as skipped
results, matching individual validation behavior.

After a batch run, choose **Export JSON Report...**. The exporter saves the exact
in-memory report represented by the displayed summary, appends `.json` when
needed, writes UTF-8 with a final newline, and atomically replaces the destination.
Temporary batch UI properties are not stored in `.blend` files. Unsaved files are
supported and are represented by `"is_saved": false` and a null source path.

The public report schema is versioned independently from the add-on. Version `1.0`
has this top-level shape:

```json
{
  "schema_version": "1.0",
  "generated_at_utc": "2026-09-28T12:00:00Z",
  "generator": {
    "tool_name": "Blender Asset Pipeline",
    "addon_version": "0.3.0",
    "blender_version": "5.2.2 LTS"
  },
  "source": {
    "blend_filepath": null,
    "is_saved": false
  },
  "policy": {
    "max_triangle_count": 100000,
    "naming_convention": "LOWER_SNAKE_CASE",
    "required_prefix": "",
    "transform_tolerance": 0.0001
  },
  "scope": {
    "type": "ALL_SCENES",
    "scenes": ["Main", "Secondary"]
  },
  "summary": {
    "objects": {},
    "checks": {},
    "geometry": {}
  },
  "objects": []
}
```

Each object record includes its name, type, sorted scene memberships,
validated/skipped state, `CLEAN`/`WARNING`/`ERROR`/`SKIPPED` status, check summary,
geometry and transform snapshots where applicable, and ordered validation checks.
Check severities remain `PASS`, `WARNING`, and `ERROR`. Internal Blender pointers
and deduplication keys are never part of the schema. This stable representation is
suitable for CI consumers and a future headless CLI, but no CLI is included yet.

### Preview-first fixer workflow

The fixer never runs as part of validation and there is no immediate "fix
everything" command:

1. Validate the active object or selected objects.
2. Expand **Fix Preview** and choose **Generate Fix Plan**.
3. Review every proposed action, explanation, risk, and unsupported reason.
4. Keep the default `SAFE` selections, use **Select All Safe**, or explicitly opt
   into individual `CAUTION` actions.
5. Choose **Apply Selected Fixes** and review the confirmation summary.
6. Confirm the operation. Blender applies the selected fixes as an undoable action.
7. Review the automatic validation results and the `FIX REPORT` plus `VALIDATION
   AFTER FIXES` output in the system console.

Generating or clearing a plan never changes an asset. A plan is discarded after an
apply operation, and running validation again also clears the old plan.

### Supported automatic fixes

- Naming normalization for `lower_snake_case`, `UpperCamelCase`, and an optional
  required prefix. Collisions use predictable pipeline-safe suffixes such as
  `_002`, rather than relying on Blender's `.001` suffix.
- Independent application of location, rotation, or scale through Blender's
  transform application behavior. Positive, finite, non-near-zero scale is
  `SAFE`; mirrored/negative scale is `CAUTION` and opt-in; zero, near-zero, and
  non-finite scale is never applied automatically.
- Removal of empty material slots when no polygons use those slots.
- Consolidation of slots that reference the exact same material datablock, with
  explicit polygon-index remapping.

Automatic mutation is refused for linked data, library overrides, shared mesh
datablocks, unsafe object hierarchies, constraints, modifiers, animation, shape
keys, delta transforms, locked channels, object-linked material slots, and other
states where the result could affect more than the previewed asset.

### Manual and unsupported fixes

The preview explains these issues but does not attempt to repair them:

- Missing image files or image texture nodes without an assigned image
- Missing UV maps
- Empty mesh geometry
- Triangle-budget violations, decimation, or other mesh optimization
- Missing material assignment or optimization beyond exact duplicate slots
- LOD and collision generation

### Risk, undo, and stale plans

- `SAFE` actions are supported and selected by default.
- `CAUTION` actions require the user to select them explicitly.
- `DESTRUCTIVE` is reserved for high-risk future operations and is never selected
  automatically.

**Apply Selected Fixes** presents object and risk counts before execution and uses
Blender's `REGISTER`/`UNDO` integration. Selection, active object, and mode are
restored where practical. Each plan stores a fingerprint of relevant state; a
renamed, transformed, materially changed, or deleted object is reported as stale
instead of receiving an outdated fix.

## Architecture

```text
blender_asset_pipeline/
|-- __init__.py             Add-on metadata and lazy entry points
|-- constants.py            Shared identifiers and version data
|-- preferences.py          Add-on configuration
|-- registration.py         Ordered Blender class/property lifecycle
|-- models/                 Typed snapshots, configuration, and results
|-- validation/             Blender-independent rules and report formatting
|-- fixing/                 Pure planning/models plus guarded Blender execution
|-- batch/                  Collection models, pure aggregation, console summary
|-- reporting/              Schema-v1 JSON, atomic writer, latest-run cache
|-- operators/              Validation, batch, report, and explicit-fix commands
|-- ui/                     Sidebar panels and transient validation/fix/batch state
`-- utils/                  Blender-to-core data adapters
tests/                      Pure-Python tests and a separate Blender smoke test
```

Adapters take read-only snapshots of Blender data. Individual and batch validation,
fix planning, JSON serialization, and report writing consume dataclasses without
depending on `bpy`; only collection, operators, UI, and explicit fix execution use
Blender APIs. Batch discovery scans each included scene once, deduplicates by
object identity internally, and validates each unique snapshot once. Validation,
fix-plan, and batch UI state use `SKIP_SAVE`.

## Development

Run the core test suite from the repository root:

```bash
python -m compileall -q blender_asset_pipeline tests
ruff check .
python -m unittest discover -s tests -v
```

GitHub Actions runs these Blender-independent checks with Python 3.10 on every
push and pull request. This matches the Python generation used by Blender 3.6 LTS,
the add-on's minimum supported Blender release.

A Blender smoke test remains separate from the normal CI job because standard
GitHub-hosted runners do not include Blender. Run it locally when Blender is
installed:

```bash
blender --background --factory-startup --python tests/blender_smoke_test.py
```

## Roadmap

- [x] Preview-first automatic asset fixer with explicit opt-in (Milestone 2)
- [x] Current-scene and all-scenes batch validation (Milestone 3)
- [x] Machine-readable JSON reports, schema version 1.0 (Milestone 3)
- Folder/project scanning
- Batch import/export
- LOD generation
- Collision generation
- Texture and material optimization
- Thumbnail rendering
- HTML reports
- Headless CLI processing
- Expanded CI/testing across supported Blender versions

## Development status

Milestone 3 is complete at version 0.3.0. Batch validation is read-only and limited
to objects already present in the current blend file. It does not scan folders,
import external assets, fix objects in bulk, provide a headless CLI, or generate
HTML. Active/selected validation and the conservative preview-first fixer remain
available and unchanged in scope.

## License

Released under the MIT License. See [LICENSE](LICENSE).
