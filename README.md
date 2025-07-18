# oct_analysis

`oct_analysis` is a Python library for processing image data from optical methods, foremost optical coherence tomography (OCT).

It provides functions for loading, segmenting and analyzing Thorlabs OCT image stacks.
These functions are accessible via direct import into Python code, and as a napari plugin.

---

## Features

- Load `.oct`, `.nii` and `.tiff` files into NumPy arrays
- Normalization and various filter options
- Semi-automated, fine-tunable window and substratum detection
- Thresholding, segmentation, and outlier removal
- Export of processed stacks and parameter settings
- GUI support (napari) for interactive labeling/analysis workflows

## Getting Started

- **[Installation Guide (Windows)](docs/INSTALL.md)**  
  Setup instructions for users and developers using PowerShell and `uv`.

- **[Usage Guide](docs/USAGE.md)**
  Step-by-step description of the GUI workflow and CLI/API examples.

- **[API Documentation](https://oct-analysis.readthedocs.io/en/latest/)**
  Full function reference and module descriptions.
  **Not up-to-date**

---

## License

MIT License - see **[LICENSE](LICENSE)** for details.