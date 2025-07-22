# Developer Installation (Windows)

This guide explains how to set up a full development environment using [`uv`](https://github.com/astral-sh/uv) and PowerShell.

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

This guide explains how to set up napari and this plugin to use it.

**Currently:** follow instructions for developers (you can ignore all the git-stuff, this is only needed for contributing)

Future: pip install

Check out the **[Usage](USAGE.md)** instructions on how to work with napari and the plugin