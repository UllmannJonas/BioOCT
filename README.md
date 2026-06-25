# BioOCT

`BioOCT` is a napari plugin for quantitative analysis of 3D optical coherence tomography (OCT) images, built around the Thorlabs `.oct` file format. It is suited for biofilm and some scaling variants.

It bundles a domain-specific set of processing functions, interactive widgets, and a reproducible batch-processing pipeline into a toolbox — designed for OCT/biofilm researchers without requiring programming expertise.

The main use cases are:

- segmenting biofilm or scaling from surrounding fixtures (substratum, optical window, feed spacer, bulk medium) in OCT image stacks with a (near-)planar substratum geometry
- recording an image processing pipeline once on a representative image, then reproducibly replaying it on a single image or across a full folder/timeseries of `.oct` files
- exporting raw and segmented data with preserved voxel geometry and physical spacing, suitable as training data for volumetric ML segmentation models

---

## Features

- Dedicated reader for Thorlabs `.oct` files
- Filtering (Median, Gaussian, Sobel) and contrast enhancement (gamma, percentile clipping, CLAHE)
- Substratum/window detection with gap interpolation, ROI selection, and reflection/area-masking tools
- Thresholding via multiple standard algorithms (Otsu, Yen, Li, Mean, Isodata, Triangle, or manual value) with live preview
- Post-processing (small-object removal) and quantitative evaluation: height maps, biovolume maps, and growth/roughness/porosity metrics export
- Export to TIFF and NIfTI with voxel spacing and affine metadata preserved
- Pipeline Manager: records processing steps as human-readable YAML, with single-layer and batch-folder replay for reproducible analysis

## Getting Started

- **[Installation Guide (Windows)](docs/INSTALL.md)**
  Setup instructions for users.


- **[Usage Guide](docs/USAGE.md)**
  Overview and guidance to plugin usage and napari.


- **[Contribute](docs/CONTRIBUTE.md)**
  Best practice workflow for contributing to the project.


## Sample Data & Example Pipelines

Three example datasets covering structurally distinct image classes are available via
```
File > Open Sample > BioOCT
```
directly in napari, or on **[Zenodo (DOI: doi.org/10.5281/zenodo.20758173)](https://doi.org/10.5281/zenodo.20758173)**:

- **Membrane with Spacer**: membrane substratum with embedded feed spacer fixtures
- **Rough Electrode**: electrode substratum with rough surface topology
- **Smooth Electrode with Shadowing**: planar electrode substratum with signal shadowing caused by thick biofilm growth

Matching pipeline YAML files for each image class are also available in the above Zenodo dataset, or via the repository in [`docs/examples/`](docs/examples/), demonstrating a complete processing workflow from raw `.oct` to segmentation and metrics export. Load them via the Pipeline Manager widget (`Load` → `Replay Single`).

---

## License

MIT License - see **[LICENSE](LICENSE)** for details.