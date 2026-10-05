# Contributing & Collaboration Guide

This guide outlines general best practices and tips for collaborative work on programming-projects together - which also apply to the `BioOCT` project.

From developer setup, to Git workflow basics, to IDE tips.

---

## 1. Developer Setup

This section is for contributing to the codebase itself. If you just want to use BioOCT, see the [User Installation Guide](INSTALL.md) instead.

### Requirements

- **[git](https://git-scm.com/)** — latest version for your platform.
- **recommended: [uv](https://github.com/astral-sh/uv)** — install from: [Homepage](https://docs.astral.sh/uv/getting-started/installation/) or [Github](https://github.com/astral-sh/uv/releases). uv manages the Python installation itself, so no separate Python install is needed.
- A text editor / development environment (IDE, e.g. VSCode)
- A terminal (PowerShell, cmd, or your editor's integrated terminal).

### Steps

1. Navigate to where you want the project folder, e.g. `cd C:\Users\<yourusername>`.
2. Clone the repository:
```
   git clone https://github.com/UllmannJonas/BioOCT.git
   cd BioOCT
```

3. Set up the environment:
```
   uv sync
```

   This creates a `.venv` and installs everything needed for development as specified in the `pyproject.toml` file in one go.

4. Activate the environment:
```
.venv\Scripts\activate
```
(deactivate with `deactivate`)

5. Enable the pre-commit hooks (one-time setup):
```
uv run pre-commit install
```

**You are ready to work on the project now.**<br>
The rest of this guide covers collaboration best-practices.


## 2. Git Workflow
### 2.1 Short Git Intro

Git is a **version control system**. It tracks every change you make to the code, so you can go back in time, compare versions, and collaborate safely with others — without overwriting each other’s work.<br>
You work in your own isolated version ("branch"), and only **merge your work into the shared project when ready.**

Few commands will cover 90% of situations:
```bash
  git clone <url>   # get the project
  git pull    # get the latest version from the online repository
  git checkout -b my-branch   # create new workspace (branch)
  git checkout branchname   # switch to other branch
  git add .   # include all changes to the next commit
  git commit -m "commit-message"    # commit your changes locally with a descriptive message
  git push    # upload your commited changes so others can see/use them
  git status    # get info about your current branch/changes/states
```
For more info, see [git's learning resources](https://git-scm.com/learn) or<br>
watch [this video](https://www.youtube.com/watch?v=e9lnsKot_SQ) for a visual guide.

Last: **Pull Requests (PR)**.
  PRs are used to merge changes from one branch to another.
  They are done on the repository website:
  1. Go to [BioOCT on Github](https://github.com/UllmannJonas/BioOCT)
  2. Switch to tab `Pull requests`
  3. Click green button `New pull request`
  4. Base = main/dev, compare = your-branch
  5. Create PR. You can then provide a description of your changes.
  6. Usually, someone else will review your changes and accept/decline the PR

### 2.2 How we use Git

We use a **main-dev** structure:

![Structure](images/main-dev.png)

That means:

- **main branch**: Is stable. Only to be changed via merge from dev -> main
- **dev branch**: You can make minor changes on this branch. But try not to, and instead use feature branches.
- **feature branch**: Standard for changes, create your own feature branch (from dev)

### 2.3 Typical Workflow to Make Changes

0. Open a console in the `BioOCT` repository folder
1. Start on dev: `git checkout dev`
2. Get latest changes: `git pull` (do this regularily)
3. Open/Switch to your feature-branch
4. Make changes, stage changes with `git add .`
5. Use `git commit -m "message"` to create version control points from staged changes
6. Upload branch+changes: First `git pull`, then `git push`
7. Implement changes: **Create Pull Request** -> request will be reviewed (reach out to collaborators)

### 2.4 Advanced Options / Mistake Correction with Git

<!-- If the table shows a terrible format in your code editor, try allowing unlimited line lenght. In VSCode it works by hitting alt+z -->
| **Scenario** | **Solution** |
| ------------ | ------------ |
| You edited files while being on the wrong branch (e.g. main).<br>You haven't commited them yet. | 1. Use `git stash` to save changes in the "stash".<br>2. Create/switch to the correct branch.<br>3. Make sure it is up-to-date (`git pull`).<br>4. Apply your stashed changes with `git stash pop` |
| You forgot to update (`git pull`) before upload (`git push`).<br> Git yells something about non-fast-forward. | 1. Use `git pull --rebase`.<br>2. Resolve any conflics (e.g. in VSCodes Merge Editor).<br>3. `git push` again. |
| Unknown scenarios.<br> You're stuck. | Reach out to collaborators.<br> Solve it together if unsure. |

---

## 3. Working Environment

A popular text editor for software developement is VSCode.<br>
In VScode for example you can add a lot of useful extensions:<br>
 -> Python / Pylance / Github Copilot / indent-rainbow / PowerShell / Git Graph / ...<br>
 -> it also makes using git much easier


## 4. Additional Useful Info

- While main and dev branches exists continuosly, a feature branch should exist as short as possible.
- Use descriptive messages for your commits: "add function to cut rhomboid", "fix bug in function_xy that caused xyz"
- Ask for help when needed - Git keeps everything (you committed/pushed), and you can always undo mistakes (you committed/pushed).
- Instead of the console, you can use GUI programs to work with Git - same principles apply<br>
 -> GitHub Desktop / Git Extensions / VSCode Extensions

**Best practices in a nutshell:**<br>
Don’t work directly on main.<br>
Pull often. Commit often. Push when stable.<br>
Ask if unsure.