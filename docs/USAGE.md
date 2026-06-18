# How to Use the BioOCT Plugin

**General behavior info:**
- The plugin never alters the original `.oct` data. Files are only read into memory, never overwritten.
- Napari works with layers, similar to e.g. Photoshop. It has a lot of layer-functionality built in, e.g. layer blending, converting layer-types, color-maps, 2D/3D view, creating projections, duplicating, etc. See [official napari documentation](https://napari.org/stable/tutorials/fundamentals/viewer.html) for more info.
- To produce ML-ready labeled data, include an **Export to NIfTI** step in your recorded pipeline. It preserves voxel spacing and affine metadata alongside the segmentation, often used for 3D-segmentation ML-models.

## Opening napari + Plugin

1. Set up the installation as described in the [Installation Guide](INSTALL.md).
2. Start napari (e.g. via doubleclick on `Start_BioOCT.bat` on Windows, or via `napari` in a CLI with activated virtual environment).
3. Open one or more `.oct` files via drag & drop, or `File > Open File(s)`. BioOCT's reader is invoked automatically for `.oct` files.
4. Access plugin widgets via `Plugins > BioOCT > [Widget Name]`. Each entry opens its own dock widget; several can be open at once and rearranged.

## Working with Widgets

Most processing widgets follow the same pattern: select an input layer (and any additional required layer, e.g. a binary mask), set parameters, and apply. The result appears as a new layer, which can then serve as input to the next widget.

Available widgets and what each one does in detail will be covered separately in the function reference once finished.

## Pipeline Manager: Recording & Batch Replay

The **Pipeline Manager** widget is the core of reproducible, repeatable processing:

- Toggling **Record Pipeline** starts capturing every applied widget step (function, input/output layers, parameters) into a YAML structure, shown live in the panel.
- The recorded pipeline can be saved to / loaded from a `.yaml` file, and individual steps can be deleted or cleared.
- **Single Replay** re-applies the recorded pipeline to a chosen layer in the current session.
- **Batch Replay** re-applies the recorded pipeline to every `.oct` file in a selected folder, one after another, including any export steps (TIFF/NIfTI/metrics) the pipeline contains.

**Tip:** In order to be applicable to different filenames without manual adjustment, the pipeline uses placeholders for:
1) the filename/initial layername (`$base`),
2) the directory for saving (`$source_dir`).

**Pro-tip:** You can edit a .yaml pipeline file manually like a .txt file (e.g. change parameter values) - but be sure not to change indentation.

## Reporting Issues

If you encounter errors or unexpected behaviour, please open an Issue:
- go to [Issues for `BioOCT` on github](https://github.com/UllmannJonas/BioOCT/issues)
- click the green button in the top right corner, `New issue`
- describe what you were trying to do and what error you encountered
- copy-paste the error message if possible
- you will get help / be notified once the error is fixed