# oct_analysis

oct_analysis is a Python library for the processing of image data for optical methods (foremost optical coherence tomography (OCT)).

# Quick Setup Guide (Currently only for Windows)

## For Users (Windows/Powershell)

1) Install uv (a modern python package manager)

   1.1) Open Windows Powershell (PS)

   1.2) Paste this into PS and hit enter:

```PS
powershell -ExecutionPolicy Bypass -c "irm https://github.com/astral-sh/uv/releases/download/0.7.19/uv-installer.ps1 | iex"
```

   1.3) add uv to you PATH as recommended by the promt after installing uv

   or

   1.3) if no promt appears, restart the PS -> uv is now ready

2) execute this line in PS and follow the instructions given in the PS:
```PS
irm https://raw.githubusercontent.com/AndreasNetsch/oct_analysis/main/setup/setup_user.ps1 | iex
```
5) Done!

## for Contributors/Developers (Windows/Powershell)
1) Install uv (a modern python package manager)

   1.1) Open Windows Powershell (PS)

   1.2) Paste this into PS and hit enter:

```PS
powershell -ExecutionPolicy Bypass -c "irm https://github.com/astral-sh/uv/releases/download/0.7.19/uv-installer.ps1 | iex
```

   1.3) add uv to you PATH as recommended by the promt after installing uv

   or

   1.3) if no promt appears, restart the PS -> uv is now ready
   
2) Install git -> https://git-scm.com/downloads
3) execute this line in PS and follow the instructions given in the PS:
```PS
irm https://raw.githubusercontent.com/AndreasNetsch/oct_analysis/main/setup/setup_dev.ps1 | iex
```
5) Done!


# OCT Labeling Workflow

### 1. Load & Normalize
- Click *Load OCT* to open a `.oct` file  
- This creates a hidden raw layer and a normalized image layer

### 2. Preprocessing
- Apply *Median Filter* to smooth noise but preserve edges  
- Apply *ROI 2D Filter* to enhance detection of horizontal edges

### 3. Window/Substratum Detection
- Use *Locate Window* to find window coordinates  
- Click *Zero Out Window* to mask it  
- Use *Locate Substratum* to detect the substratum  
- Click *Zero Out Substratum* to mask it  
  → Internally, the coordinates are located using the `roi_filtered` layer  
  → The masking is applied to the `median_filtered` layer (important for binarization)

### 4. Postprocessing
- Use *Increase Contrast* to improve binarization accuracy  
- Adjust *Threshold* to binarize — changing the value auto-calls the function  
  → Threshold is applied to the `no_substratum` layer  
  → Zero-values are ignored  
- Optionally use *Remove Outliers* to clean up background noise (auto-call)

### 5. Save
- Use *Save stack+mask_stack* to export normalized & binary layers as `.nii.gz`  
- Use *Save Settings* to export a `.json` of all current parameters


## Features

The oct_analysis python package includes various functions for:

- Unpacking *.oct files and loading tiff files as numpy array
- Preprocessing functions to identify and remove objects/boundaries
- Image segmentation and binarization
- Post-processing funtions for the calcuation and saving of structural parameters from the imaging stacks

## Usage
The documentation can be found in https://oct-analysis.readthedocs.io/en/latest/index.html

Examples for the usage of the functions are described in https://github.com/AndreasNetsch/oct_analysis/tree/main/examples

```python
from oct_analysis import (
    read_tiff,
    select_tiff_folder,
    convert_to_8bit,
    find_substratum,
    voxel_count,
    find_max_zero,
    untilt,
    generate_Height_Map
)
```


### Documentation

This project uses Sphinx for documentation. To build the documentation locally:

```bash
cd docs
make html
```

The generated documentation will be available in `docs/build/html/index.html`.

#### ReadTheDocs Integration

The documentation is also configured to be built automatically on [ReadTheDocs](https://readthedocs.org/). To set it up:

1. Push your code to GitHub
2. Sign up for a ReadTheDocs account
3. Import your repository on ReadTheDocs
4. ReadTheDocs will automatically build and host the documentation

You can customize the build process by modifying `.readthedocs.yml` and the Sphinx configuration files in the `docs` directory.

## CI/CD

This project uses GitHub Actions for:

- Running tests on multiple Python versions
- Linting the code
- Building and publishing the package to PyPI when a new version tag is pushed

### Creating Releases

The CI/CD pipeline is configured to automatically build and publish the package to PyPI when a new version tag is pushed to the repository. This process ensures that only properly versioned, tagged releases get published.

To create and publish a new release:

1. Update the version number in `setup.py`
2. Commit your changes:
   ```bash
   git add setup.py
   git commit -m "Bump version to x.y.z"
   ```
3. Create a new version tag (tag name must start with "v"):
   ```bash
   git tag vx.y.z
   ```
4. Push the tag to GitHub:
   ```bash
   git push origin vx.y.z
   ```

Once the tag is pushed, GitHub Actions will:

1. Run all tests on multiple Python versions
2. If tests pass, build the package
3. Publish the package to PyPI using the configured PyPI API token

Note: Make sure you've added a `PYPI_API_TOKEN` secret to your GitHub repository settings under "Settings > Secrets and Variables > Actions" before triggering a release.

## License

MIT License
