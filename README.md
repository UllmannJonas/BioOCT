# oct_analysis

`oct_analysis` is a napari plugin for processing image data from optical coherence tomography (OCT) from Thorlabs .oct fileformat.


It provides widgets for interactive usage of functions from the `bio-oct`-Python package.

The main use cases are:

- segment biofilm growing on flat surfaces from optical window and substratum
- fast batch-processing of timeseries data
- creating labeled data for semantic segmentation by ML


NOTE: For exporting data as nifti (needed for ML training via nnUnet), the napari-nifti plugin is recommended.

---

## Features

- Enable napari to open `.oct` files
- Normalization and various filter options
- Semi-automated, fine-tunable window and substratum detection
- Thresholding, segmentation, and outlier removal
- Export of parameter settings

## Getting Started

- **[Installation Guide (Windows)](docs/INSTALL.md)**
  Setup instructions for users and developers using PowerShell and `uv`.


- **[Usage Guide](docs/USAGE.md)**
  Overview and guidance to further information about the plugin usage and napari.


- **[Contribute](docs/CONTRIBUTE.md)**
  Best practice workflow for contributing to the project.


---

## License

MIT License - see **[LICENSE](LICENSE)** for details.