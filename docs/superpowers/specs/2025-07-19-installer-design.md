# DeepSleuth Installer Scripts — Design Spec

**Date:** 2025-07-19
**Status:** Approved

## Goal

Make DeepSleuth installation as simple as running a single script — `install.sh` (macOS/Linux) or
`install.bat` (Windows) — while still requiring Python 3.11+ and Node.js 18+ as system
prerequisites.

## Target User

Technically capable but not a developer. Can run a script in a terminal. Should not need to
debug Python environments, resolve pip conflicts, or understand Node build tooling.

## Platforms

- **Windows** — `install.bat` (batch script, wide compatibility)
- **macOS** — `install.sh` (bash, POSIX)
- **Linux** — `install.sh` (bash, POSIX)

## Script Strategy

Both scripts live in the repo root. They are idempotent — re-running is safe and fast (skips
completed steps or uses `--upgrade`).

Model weights (`xception_best.pth`, `face_landmarker.task`) are bundled into GitHub Releases
(e.g., `weights-v1.0.zip`). Scripts download and extract them automatically, using a
hardcoded `SCRIPT_VERSION` variable inside each script (bumped with each release) to build
the download URL. This avoids depending on `git` being available.

## Prerequisite Checking (all platforms)

At startup, each script verifies:

| Prerequisite | Check | Failure message |
|---|---|---|
| **Python 3.11+** | `python3 --version` (macOS/Linux), `py -3.11 --version` then `python --version` (Windows) | "Python 3.11+ not found. Download from https://python.org" |
| **Node.js 18+** | `node --version` | "Node.js 18+ not found. Download from https://nodejs.org" |
| **CUDA (Windows/Linux only)** | `nvidia-smi` exit code | Not a hard failure — CPU-only PyTorch installed as fallback |
| **Git (optional)** | `git --version` | Only needed if not running from a cloned repo |

If a prerequisite is missing, the script prints a clear error with a download link and exits
with code 1. On re-run, the user can continue from the same point.

## CUDA Detection

On Windows and Linux:

1. Run `nvidia-smi` and check exit code.
2. If non-zero, no NVIDIA GPU — install CPU-only PyTorch.
3. If zero, parse CUDA version from `nvidia-smi` output to select the appropriate index URL
   (`cu118`, `cu121`, etc.). Default to `cu118` if version can't be determined.

On macOS, always install CPU-only PyTorch.

## Installation Flow (6 steps)

Both scripts follow the same numbered flow:

```
[1/6] Checking prerequisites...
[2/6] Creating Python virtual environment...
[3/6] Installing PyTorch and dependencies...
[4/6] Downloading model weights...
[5/6] Building frontend...
[6/6] Done!
```

### Step 1: Check Prerequisites

- Python version ≥ 3.11
- Node.js version ≥ 18
- CUDA detection (Windows/Linux)
- Print summary of what was found

### Step 2: Create Virtual Environment

- Create `.venv` in the project root if it doesn't exist.
- Activate and upgrade pip.

### Step 3: Install Dependencies

- Install PyTorch first with the correct index URL (CUDA or CPU).
- Then install remaining deps via `pip install -e .` (reads from `pyproject.toml`).

### Step 4: Download Model Weights

- Fetch `weights-v<version>.zip` from GitHub Releases URL.
- Show curl progress bar (or write indicator on Windows).
- Extract into `weights/` directory.
- Skip if both `weights/xception_best.pth` and `weights/face_landmarker.task` already exist
  and are non-empty (checked via `-s` in bash, file size check in batch).

### Step 5: Build Frontend

- `cd frontend && npm install && npm run build`
- On Windows, `cd` is `pushd` / `popd` to handle directory restoration.

### Step 6: Success

Print:

```
DeepSleuth installed successfully!

Run:   deepsleuth
Or:    python -m backend.cli

Open http://127.0.0.1:8000 in your browser.
```

## Error Handling

- Each step has a descriptive error message with a suggested fix.
- Script exits with non-zero code on failure.
- User can fix the issue and re-run — script picks up where it left off (venv, node_modules,
  weights persist).
- Weight download uses curl `--max-time 120` to avoid indefinite hanging.
- No silent failures — every `if` / `$?` check prints a message.

## `install.sh` Details (macOS & Linux)

- Pure bash, POSIX-compatible.
- Commands used: `python3`, `node`, `nvidia-smi`, `curl`, `unzip`, `npm`.
- Detects: macOS vs Linux (for platform-specific messages only; logic is identical).
- Stages: same 6-step flow above.
- Shebang: `#!/usr/bin/env bash`.

## `install.bat` Details (Windows)

- Batch script, runs on Windows 10+ without additional runtime.
- Uses `py -3.11` (Python launcher) as first choice, `python` as fallback.
- CUDA check via `nvidia-smi` in PATH.
- Weight download via `curl.exe` (built into Windows 10+).
- Since batch has poor progress-bar support, prints clear step indicators and relies on
  curl's `--progress-bar` where possible.
- For directory management: `pushd` / `popd`.

## (Non-)Goals

### In scope
- Cross-platform install scripts (bash + batch)
- CUDA-aware PyTorch installation
- Automatic weight download from GitHub Releases
- Frontend build automation

### Out of scope
- Self-contained executables (no PyInstaller, no bundled runtimes)
- Desktop shortcuts / system-wide installation
- Package manager distribution (Homebrew, apt, scoop, etc.)
- Docker images
- GUI installer

---

*Approved via brainstorming session on 2025-07-19.*
