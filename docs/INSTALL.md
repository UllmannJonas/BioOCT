# Installation (Windows)

We provide a setup file for users with no python environment experience.
With that, no prior knowledge is needed, just two easy steps will get you started.
If you prefer to have more control over the setup, refer to the **Python environment installation** below.

## Step 1: Download the starter file

Download from Github: **[Start_BioOCT.bat](https://github.com/UllmannJonas/BioOCT/blob/main/Start_BioOCT.bat)**

Save it somewhere you'll find again, e.g. your Desktop.

## Step 2: Excecute

Double-click `Start_BioOCT.bat`. A console window will open and set everything up automatically. This can take a few minutes the first time. Once it's done, napari including the BioOCT plugin opens by itself.

After initial setup, executing the same file will start up much faster since setup steps only run once.

You may inspect the file's content by renaming the suffix to ".txt" and opening it via any text editor.

---

## Python environment installation

BioOCT is available on pypi and can be installed in your preferred environment via
```
pip install bio-oct
```
or other packet managers such as `uv`.

Note that `napari` and the QT backend `pyqt6` are not included in `bio-oct` and need to be installed additionally. Further, the `napari-nifti` plugin is recommended for reading NIfTI-files in napari.

---

## Troubleshooting

- **Error message mentions "os error 5" or "failed to rename file":** this is a [known issue](https://github.com/astral-sh/uv/issues/1491) caused by antivirus software interfering with the setup process. Try temporarily disabling real-time protection and run the file again
- **Any other error:** copy the error message from the console and open an issue [here](https://github.com/UllmannJonas/BioOCT/issues), describing what happened.

For guidance on using the plugin once it's running, see the [User Guide](USAGE.md).