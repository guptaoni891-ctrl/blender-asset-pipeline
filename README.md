# Blender Asset Pipeline

Blender Asset Pipeline is an installable Blender add-on for checking whether mesh
assets are ready to enter a game-content pipeline. Milestone 1 is deliberately
validation-only: it reports problems but never changes an object, mesh, material,
image, or scene setting.

Version: **0.1.0**

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

## Installation

1. Download or clone this repository.
2. Create a ZIP whose top-level folder is `blender_asset_pipeline` (do not ZIP the
   entire repository). From the repository root, for example:

   ```powershell
   Compress-Archive -Path blender_asset_pipeline -DestinationPath blender_asset_pipeline-0.1.0.zip
   ```

3. In Blender, open **Edit > Preferences > Add-ons**, choose **Install...**, select
   the ZIP, and enable **Asset Pipeline: Game Asset Validator**.

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
   Validator**.

Validation is read-only. Applying transforms, renaming assets, creating UVs, and
repairing material or texture references remain explicit user actions in this
milestone.

## Architecture

```text
blender_asset_pipeline/
|-- __init__.py             Add-on metadata and lazy entry points
|-- constants.py            Shared identifiers and version data
|-- preferences.py          Add-on configuration
|-- registration.py         Ordered Blender class/property lifecycle
|-- models/                 Typed snapshots, configuration, and results
|-- validation/             Blender-independent rules and report formatting
|-- operators/              Active/selection validation commands
|-- ui/                     Sidebar panel and transient result state
`-- utils/                  Blender-to-core data adapters
tests/                      Pure-Python unit tests
```

The adapter takes a read-only snapshot of Blender data. Validation consumes only
dataclasses, which keeps policy separate from `bpy` and makes the core usable in
future headless and automated workflows.

## Development

Run the core test suite from the repository root:

```bash
python -m unittest discover -s tests -v
python -m compileall -q blender_asset_pipeline tests
```

A Blender smoke test can be run when Blender is installed:

```bash
blender --background --factory-startup --python tests/blender_smoke_test.py
```

## Roadmap

- Automatic asset fixer (explicit opt-in; not part of Milestone 1)
- Batch validation across scenes and project folders
- Batch import/export
- LOD generation
- Collision generation
- Texture and material optimization
- Thumbnail rendering
- JSON and HTML reports
- Headless CLI processing
- Expanded CI/testing across supported Blender versions

## Development status

Milestone 1 is complete at version 0.1.0. The public validation model and Blender
adapter are intentionally separated so later milestones can add fixers and batch
processing without coupling those features to the sidebar UI.

## License

Released under the MIT License. See [LICENSE](LICENSE).
