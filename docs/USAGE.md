# How to Use the Napari Plugin
**General behavior info:**
- The plugin will never alter the original .oct data
- Napari works with layers, similar to e.g. photoshop. It has a lot of layer-functionality builtin, e.g. layer blending, converting layer-types, color-maps, 2D/3D view, creating projections, duplicating, etc. I recommend checking it out. See [napari-viewer-docs](https://napari.org/stable/tutorials/fundamentals/viewer.html) for more info
- To create ML-ready labeled data, always save your segmentations as nifti (Batch processing will do this automatically).

## Opening Napari + Plugin

1. Set up the installation as described >[here](INSTALL.md)<.
2. Start Napari by double-clicking launch_napari.bat (on Windows).
3. Napari will open (first time after installing can take some time, due to python files getting compiled).
*Now you should see the napari interface. You can now open .oct file(s) by drag&drop or "File > Open File(s)". Try it!*

4. To access the OCT-plugin, click on `Plugins` (at the top), choose OCTool.
5. On the right, the plugins widgets will appear.

---

## Feature Overview
### Functions in Load/Save Tab

- **Clear Layers and Reset Session**
 Reverts napari back in a clean state.

 Use this before opening a new file.

 *This will be no longer neccessary after a future update*


- **Update Widget Parameters**
 Adjusts Widget-Settings max values according to the image.

 Use this after loading a file into napari.

 *This will be no longer neccessary after a future update*


- **Create "working copy"-Layer**
 Creates a working copy that most widgets work with.

 *Currently, this is the way to make the segmentation. In the future, you should be able to choose which layer to manipulate with any widget.*


- **Export Current Settings**
 Exports the settings from all widgets into a JSON-file.

 Use this to export settings that you want to apply for a batch of images.


**Note: Saving segmented data (binary and original) is covered by other plugins. Use "File > Save Selected Layers"**
- saving data as tiff: possible via napari-builtins
- saving data as nifti: possible via napari-nifti
---

### Functions in Pre-Process Tab

- **B-Scan Selection**
  Keep B-Scans only in selected range.


- **Locate Window**
 Detects highest-intensity pixel between ymin and ymax for each A-Scan, with optional vertical offset.

 Parameters: `ymin` (upper bound), `ymax` (lower bound), `y_offset` (manual shifting of found pixel)

 Works with: `Working Copy`

 Creates: `window_coords`-Layer (for visualization)


- **Horizontal Cutoff**
  Cuts upper part of stack by choosing horizontal line. Can be used instead of `Locate Window`, if no window is visible, but the top area of the image is darker than average.

  Parameters: `cutoff_y` (axial coordinate for cutting)

  Works with: `Working Copy`

  Creates: `window_coords`-Layer (for visualization)


- **Zero Out Window**
 Changes values above (and including) the detected window coordinates to 0.

 Works with: `window_coords`, `Working Copy`

 Removes: `window_coords`


- **Apply Median Filter**
 Reduces high-frequency noise by median filtering with a 2D kernel in the lateral dimensions.

 Parameter: `kernel edge length`

 Works with: `Working Copy`


- **Select Substack**
 Select only a specified region of the stack (axial direction).

 Parameter: `ymin`, `ymax`

 Works with: `Working Copy`

 Creates: `substack`


- **Apply Canny Edge Filter**
 Finds Canny Edges in the stack.

 Parameter: `Weak Edge Threshold`, `Strong Edge Threshold`, `Gaussian Blur Sigma`

 Works with: `Working Copy`

 *Note: here, you have to experiment a bit to create good edges. But once you found good settings, the edges should be very good.*


- **Locate Substratum**
 Detects highest-intensity pixel between ymin and ymax for each A-Scan, with optional vertical offset.

 Works with: `Working Copy`

 Creates: `substratum_coords`-Layer (for visualization)

 *Note: When using together with Canny Edge Detection, there can be areas with no substratum edge found ("holes"). In this case, you can use `Clean Substratum Coordinates`. However, try adjusting the Canny Edge Settings first, so that you have minimal holes.


- **Clean Substratum Coordinates**
 Removes outliers from the detected `substratum_coords` and fills holes by linear interpolation.

 Works with: `substratum_coords`


- **Zero Out Substratum**
 Changes values below (and including) the detected substratum coordinates to 0.

 Works with: `substratum_coords`, `Working Copy`

 Removes: `substratum_coords`


- **Confirm Segmentation**
  Replaces valid data (= data below window and above substratum) from `Working Copy` with original values from Original-`"filename"`-Layer.

  Works with: Original-`"filename"`-Layer, `Working Copy`

---

### Functions in Binarize Tab

- **Increase Contrast**
 Enhances image contrast by removing lower and upper percentile intesity-values. Then stretching the histogram to the full range 0-1.

 Parameters: `percentile` (Percentage of lower/upper histogram values to be clipped)

 Works with: non-zero values of `Working Copy`


- **Gauss Filter**
  Reduce gaussian noise after contrast enhancement to ensure clean binarization.

  Parameters: `sigma` (Intensity and Size of Gaussian Filter-Kernel)

  Works with: `Working Copy`


- **Calculate Thresholds**
 Calculate thresholds for given stack. Returns thresholds from methods: `Yen` `Li` `Otsu` `Isodata` `Triangle`. A histogram shows the position of the thresholds. A new widget is created, where User can try and select one threshold to apply.

 Works with: non-zero and non-one values of `Working Copy`

 Creates: `Binary`-Layer


- **Remove Outliers**
 Removes small connected components in binary using a user-defined connected-voxel-size threshold.

 Parameters: `outlier size`

 Works with: `Binary`


- **Confirm Binarization**
 Removes all layers, keeping only the `Binary` and Original-`"filename"`-Layer.

---

### Functions in Evaluate Tab

- **Calculate and Save Biofilm Metrics**
 Creates Height Map, Biovolume Map and saves PNGs of them in the .oct source-folder. Calculates metrics from the data (roughness, min/max/mean height, etc.) and saves as .csv file.

 Set `Max Height HM` and `Min Height SC` with full timeseries in mind to get consistent calculations and colormaps for all timesteps


---

### Functions in Batch-Tab

- **Load OCT Timeseries**
 Load 4D-OCT data either from a folder or from zarr file.

 *What the heck is a zarr file?* -> During loading of many OCT-files from a folder, a zarr-file will be created. It is essentially also a folder, which contains the timeseries-data as "chunks" (you can imagine one C-Scan gets chopped into maybe 10 chunks). The benefit: You can view the 4D-data continuously with napari, plus it makes batch processing easier and faster.


- **Load Settings and Process Batch**
 Process a batch of images with the exported settings.


---

### Notes
**If you encounter errors or unexpected behaviour, please open an Issue:**
- go to [Issues for `oct-analysis`](https://gitlab.kit.edu/kit/ebi/dvgw/watertechnology/oct-analysis/-/issues)
- click blue button in the top right corner `New Item`
- Describe what you were trying to do and what error you encountered
- Copy-Paste the error message if possible
- You will get help/noticed once the error is fixed