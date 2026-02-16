# Developer Installation (Windows)

This guide explains how to set up a full development environment using [`uv`](https://github.com/astral-sh/uv) and [git](https://git-scm.com/), setting you up to contribute to the project.

*Refer to the **User Installation Guide** below if you simply want to use the tools provided.*

## Requirements

- **[git](https://git-scm.com/)**
  Install the latest version for Windows.
- **[Python](https://www.python.org/downloads/windows/)**
  Install any Version **>=3.11**
- **[uv](https://github.com/astral-sh/uv)**
  Go to their github and choose one version-tag to download, or use this
  PowerShell command to install uv from tag 0.7.21: `powershell -ExecutionPolicy Bypass -c "irm https://github.com/astral-sh/uv/releases/download/0.7.21/uv-installer.ps1 | iex"`
- PowerShell / cmd terminal

## Steps

1. **Open Terminal and Navigate to Target Location**
  Start > Search > "PowerShell" or "cmd" > Launch

  Navigate to your desired folder to set up the workspace using `cd Your\desired\path`
    (recommended path: `C:\Users\<yourusername>`. A folder "oct_analysis" will be created there)

2. **Clone the Repository**
  Note: To use "git clone" you need access to the repository via SSH or a Token.

    Refer to the documentation at [docs.gitlab.kit.edu/getting_started](https://docs.gitlab.kit.edu/en/getting_started/).
  command: `git clone "https://gitlab.kit.edu/kit/ebi/dvgw/watertechnology/oct-analysis.git"`

  Navigate into the repository with `cd oct_analysis`

3. **Setup the Virtual Environment**
  Command to create: `uv venv`

  Command to activate: `.venv\Scripts\activate`

  (Command to deactivate): `deactivate`

  Install project dependencies: `uv sync` (in case of permission error: repeat "uv sync")

**You are ready to work on the project now. For guidance on best-practices for collaboratorive developement, see >[Contribute](CONTRIBUTE.md)<**

---

# User Installation (Windows)

## Requirements

- **[Python](https://www.python.org/downloads/windows/)**
  Install any Version **>=3.12**
- **[uv](https://github.com/astral-sh/uv)**
  Open PowerShell (Start > Search "Powershell" > Launch)

  PowerShell command to install uv: (`powershell -ExecutionPolicy Bypass -c "irm https://github.com/astral-sh/uv/releases/download/0.7.21/uv-installer.ps1 | iex"`)

  Follow instructions from uv after installation if any appear


## Steps

1. **Download the repository as a ZIP-File**
  Navigate to the [oct-analysis repository](https://gitlab.kit.edu/kit/ebi/dvgw/watertechnology/oct-analysis) in your browser

  Click on the button `<> Code` and choose `Download ZIP` from the dropdown menu

  Store it in your desired location.

  (recommended path: `C:\Users\<yourusername>`.)

  Unpack the ZIP-File.


2. **Open the directory with PowerShell**
  Start > Search "Powershell" > Launch

  Navigate into the directory with `cd C:\Path\to\folder\oct_analysis`


3. **Setup the Virtual Environment**
  Inside your PowerShell session, use the following commands:

  Command to create environment: `uv venv`

  Command to activate the environment: `.venv\Scripts\activate`

  Install project dependencies: `uv sync` (in case of permission error: repeat "uv sync")

  Install additional required dependencies:

  - `uv pip install pyqt6 napari-nifti`
  - `uv pip install \\129.13.178.141\oct\03_Toolbox\bio-oct\bio_oct-0.2.0-py3-none-any.whl` (needs access to OCT-Server)


**You are ready to use the projects tools now. For instructions on how to work with napari and the plugin, see >[User Guide](USAGE.md)<**