# Developer Installation (Windows)

This guide explains how to set up a full development environment using [`uv`](https://github.com/astral-sh/uv) and PowerShell, setting you up to contribute to the project.  
*Refer to the **User Installation Guide** below if you simply want to use the tools provided.*

## Requirements

- **[Git](https://git-scm.com/)**  
  Install the latest version for Windows.
- **[Python](https://www.python.org/downloads/windows/)**  
  Install any Version **>=3.11**
- **[uv](https://github.com/astral-sh/uv)**  
  PowerShell command to install uv: (`powershell -ExecutionPolicy Bypass -c "irm https://github.com/astral-sh/uv/releases/download/0.7.21/uv-installer.ps1 | iex"`)
- PowerShell terminal (recommended)

## Steps

1. **Open PowerShell and Navigate to Target Location**  
  Start > Search > "PowerShell" > Launch  
  Navigate to your desired folder to set up the workspace using `cd Your\desired\path`  
    (recommended path: `C:\Users\<yourusername>`. A folder "oct_analysis" will be created there)

2. **Clone the Repository**  
  PowerShell command: `git clone "https://github.com/AndreasNetsch/oct_analysis.git"`  
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
  Install any Version **>=3.11**
- **[uv](https://github.com/astral-sh/uv)**  
  Open PowerShell (Start > Search "Powershell" > Launch)
  PowerShell command to install uv: (`powershell -ExecutionPolicy Bypass -c "irm https://github.com/astral-sh/uv/releases/download/0.7.21/uv-installer.ps1 | iex"`)  
  Follow instructions from uv after installation if any appear

## Steps

1. **Download the repository as a ZIP-File**  
  Navigate to the [oct_analysis repository](https://github.com/AndreasNetsch/oct_analysis.git) in your browser  
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
  (Command to deactivate): `deactivate`  
  Install project dependencies: `uv sync` (in case of permission error: repeat "uv sync")

**You are ready to use the projects tools now. For instructions on how to work with napari and the plugin, see >[User Guide](USAGE.md)<**