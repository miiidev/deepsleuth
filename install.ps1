<#
.SYNOPSIS
    Installs DeepSleuth and its dependencies for Windows.
.DESCRIPTION
    Checks for Python, creates a virtual environment, installs Python
    dependencies, downloads model weights, and optionally creates a
    desktop shortcut.
#>

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

$ErrorActionPreference = 'Continue'

function Write-Step {
    param([string]$Message)
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Write-Error {
    param([string]$Message)
    Write-Host "ERROR: $Message" -ForegroundColor Red
}

function Write-Success {
    param([string]$Message)
    Write-Host "$Message" -ForegroundColor Green
}

# --- Step 1: Check Python ---
Write-Step "Checking Python installation"

$python = $null
$pythonPath = $null

$pythonCandidates = @("python3", "python")
foreach ($prog in $pythonCandidates) {
    $pythonPath = (Get-Command $prog -ErrorAction SilentlyContinue).Source
    if ($pythonPath) { $python = $prog; break }
}

if (-not $python) {
    Write-Error "Python 3.11+ is required but was not found."
    Write-Host ""
    Write-Host "Install Python 3.11 from the Microsoft Store or run:"
    Write-Host "  winget install Python.Python.3.11"
    Write-Host ""
    Write-Host "After installing Python, re-run this script."
    Read-Host "Press Enter to exit"
    exit 1
}

# Verify version >= 3.11
$versionOutput = & $python --version 2>&1
if ($versionOutput -match 'Python (\d+)\.(\d+)') {
    $major = [int]::Parse($matches[1])
    $minor = [int]::Parse($matches[2])
    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 11)) {
        Write-Error "Python 3.11+ required, found $major.$minor. Please upgrade."
        Read-Host "Press Enter to exit"
        exit 1
    }
} else {
    Write-Error "Could not parse Python version: $versionOutput"
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Success "Found Python $major.$minor at $pythonPath"

# --- Step 2: Create virtual environment ---
Write-Step "Setting up virtual environment"

$venvPath = Join-Path $repoRoot ".venv"

if (-not (Test-Path $venvPath)) {
    & $python -m venv $venvPath
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to create virtual environment."
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Success "Virtual environment created at .venv"
} else {
    Write-Success "Virtual environment already exists, skipping"
}

$pip = Join-Path $venvPath "Scripts" "pip.exe"
$pythonVenv = Join-Path $venvPath "Scripts" "python.exe"

# --- Step 3: Install dependencies ---
Write-Step "Installing Python dependencies (this may take a few minutes)"

& $pip install -e "$repoRoot"
if ($LASTEXITCODE -ne 0) {
    Write-Error "pip install failed. Check the output above for details."
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Success "Python dependencies installed"

# --- Step 4: Download model weights ---
Write-Step "Downloading model weights"

$weightsDir = Join-Path $repoRoot "weights"
if (-not (Test-Path $weightsDir)) {
    New-Item -ItemType Directory -Path $weightsDir -Force | Out-Null
}

# Resolve the latest release tag from GitHub API
$owner = "miiidev"
$repo = "deepsleuth"

if ($env:DEEPSLEUTH_WEIGHTS_URL) {
    $baseUrl = $env:DEEPSLEUTH_WEIGHTS_URL
} else {
    Write-Host "  Looking up latest release..."
    try {
        $apiUrl = "https://api.github.com/repos/$owner/$repo/releases/latest"
        $release = Invoke-RestMethod -Uri $apiUrl -ErrorAction Stop
        $tag = $release.tag_name
        $baseUrl = "https://github.com/$owner/$repo/releases/download/$tag"
        Write-Success "  Found latest release: $tag"
    } catch {
        Write-Error "  Could not fetch latest release info: $_"
        Write-Host "  Falling back to 'latest' tag..."
        $baseUrl = "https://github.com/$owner/$repo/releases/latest/download"
    }
}

$weightFiles = @(
    @{ Name = "xception_best.pth"; Description = "XceptionNet model weights" },
    @{ Name = "face_landmarker.task"; Description = "MediaPipe face landmarker model" }
)

foreach ($wf in $weightFiles) {
    $destPath = Join-Path $weightsDir $wf.Name
    if (Test-Path $destPath) {
        Write-Success "  $($wf.Name) already exists, skipping"
        continue
    }

    $url = "$baseUrl/$($wf.Name)"
    Write-Host "  Downloading $($wf.Description)..."
    try {
        Invoke-WebRequest -Uri $url -OutFile $destPath -ErrorAction Stop
        Write-Success "  Saved to weights/$($wf.Name)"
    } catch {
        Write-Error "  Failed to download $($wf.Name): $_"
    }
}

# --- Step 5: Verify installation ---
Write-Step "Verifying installation"

$checks = @(
    @{ Path = "Scripts\python.exe"; Label = "Python executable" },
    @{ Path = "Scripts\deepsleuth.exe"; Label = "deepsleuth CLI" }
)

$allOk = $true
foreach ($check in $checks) {
    $fullPath = Join-Path $venvPath $check.Path
    if (Test-Path $fullPath) {
        Write-Success "  [OK] $($check.Label)"
    } else {
        Write-Error "  [FAIL] $($check.Label) not found at $fullPath"
        $allOk = $false
    }
}

# Check weights
$weightChecks = @(
    @{ Path = "xception_best.pth"; Label = "XceptionNet weights" },
    @{ Path = "face_landmarker.task"; Label = "Face landmarker model" }
)

foreach ($check in $weightChecks) {
    $fullPath = Join-Path $weightsDir $check.Path
    if (Test-Path $fullPath) {
        Write-Success "  [OK] $($check.Label)"
    } else {
        Write-Error "  [FAIL] $($check.Label) not found at $fullPath"
        $allOk = $false
    }
}

if (-not $allOk) {
    Write-Error "Some components are missing. Check the errors above."
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Success "`nDeepSleuth installed successfully!"

# --- Step 6: Desktop shortcut ---
Write-Step "Creating desktop shortcut"

$createShortcut = Read-Host "Create a desktop shortcut for DeepSleuth? (Y/n)"
if ($createShortcut -ne 'n' -and $createShortcut -ne 'N') {
    $desktop = [Environment]::GetFolderPath("Desktop")
    $shortcutPath = Join-Path $desktop "DeepSleuth.lnk"

    $wshShell = New-Object -ComObject WScript.Shell
    $shortcut = $wshShell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = "powershell.exe"
    $shortcut.Arguments = "-NoExit -Command `"cd '$repoRoot' && .\.venv\Scripts\python -m backend.cli`""
    $shortcut.WorkingDirectory = $repoRoot
    $shortcut.Description = "DeepSleuth - Local deepfake video detection"
    $shortcut.Save()

    Write-Success "Shortcut created at $shortcutPath"
} else {
    Write-Host "Skipping desktop shortcut"
}

Write-Host "`nYou can now run DeepSleuth by opening a terminal in $repoRoot and typing:"
Write-Host "  .\.venv\Scripts\deepsleuth" -ForegroundColor Green
Write-Host "`nor double-click the DeepSleuth shortcut on your desktop."
Read-Host "`nPress Enter to exit"
