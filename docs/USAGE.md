# How to Use the Napari Plugin

## Opening Napari + Plugin

1. Set up the installation as described >[here](INSTALL.md)<.
2. Activate your virtual environment. Then type `napari`
3. Napari will open (first time after installing can take some time, due to python files getting compiled).
4. In napari, click on `Plugins` (at the top), choose OCTool.
5. On the right, the plugins widgets will appear

## Feature Overview
### Functions

- **Load OCT**
 Opens a .oct file, extracts image and metadata, normalizes intensities.  
 Creates: `Original layer (raw, hidden)`, `base layer (normalized, visible)`

- **Apply Median Filter**
 Reduces high-frequency noise by median filtering with a 2D kernel in the istropic dimensions: xz.  
 Works with: `base layer`  
 Creates: `target layer (from base)`  
 *Note:* this is the heaviest processing step. larger kernel takes longer. size=1 does no filtering.

- **Enhance Horizontal Edges (ROI Filter)**
 Applies an averaging filter in the shape of a horizontal 2D plane to highlight horizontal features. It is oriented the same way as the median filter. 
 Parameter: kernel edge length  
 Works with: `target layer`  
 Creates: `edge_enhanced layer (from target)`  
 *Note:* size=1 does no filtering.

- **Locate Window**
 Detects highest-intensity pixel between ymin and ymax, with optional vertical offset.
 Works with: `edge_enhanced layer`  
 Creates: `window_coords layer (for visualization)`

- **Zero Out Window**
 Changes voxel-values above (and including) the detected window coordinates.
 Works with: `window_coords layer`, `target layer`
 Removes: `window_coords layer`

- **Locate Substratum**
 Detects highest-intensity pixel between ymin and ymax, with optional vertical offset.  
 Works with: `edge_enhanced layer`  
 Creates: `substratum_coords layer (for visualization)`

- **Zero Out Substratum**
 Changes voxel-values below (and including) the detected substratum coordinates.
 Works with: `substratum_coords layer`, `target layer`
 Removes: `substratum_coords layer`, `edge_enhanced layer`

- **Increase Contrast**
 Enhances image contrast by removing lower and upper percentile pixel-values first. Then stretching the histogram to the full range 0-1. Optional histogram display.
 Works with: `target layer (0-values ignored)`  
 Creates: `bin_base layer (temp, not binary yet)`

- **Binarize**
 Apply a threshold to binarize interactively.
 Works with: `bin_base layer`
 Creates: `binary layer`

- **Remove Outliers**
 Removes small connected components in binary using a user-defined connected-voxel-size threshold.
 Works with: `binary layer`

- **Confirm Binarization**
 Cleans up all intermediate layers, keeping only the final binary mask and the raw Original.
 Removes: all but `binary layer` and `Original layer`

- **Save Settings**
 Exports the current parameter settings of the widgets as a JSON file

- **Save Original & Binary**
 Exports both the raw and binary stacks as .nii.gz files, with metadata (instrument model, wavelength, timestamp) encoded in the NIfTI header.

### Layer Overview

<!-- If the table shows a terrible format in your code editor, try allowing unlimited line lenght. In VSCode it works by hitting alt+z -->
| Layer Name          | Content                               | Created from            |
| ------------------- | ------------------------------------- | ----------------------- |
| `Original`          | Raw OCT volume with metadata          | .oct file               |
| `base`              | Normalized OCT volume                 | .oct file               |
| `target`            | Preprocessing workspace               | `base`                  |
| `edge_enhanced`     | Horizontally filtered version         | `target`                |
| `window_coords`     | Window positions (as label layer)     | `edge_enhanced`         |
| `substratum_coords` | Substratum positions (as label layer) | `edge_enhanced`         |
| `bin_base`          | Contrast-enhanced volume              | `target (0s ignored)`   |
| `binary`            | Final binary segmentation             | `bin_base`              |

### Notes

- All coordinate layers (*_coords) store the corresponding raw coordinate arrays in the layers metadata.
- The contrast function ignores zero-valued pixels for percentile calculations.
- Visibility of layers is automatically adjusted throughout the pipeline to maintain workflow focus.
- If required layers are missing, a popup is displayed in Napari.