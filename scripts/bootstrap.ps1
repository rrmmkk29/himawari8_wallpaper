param(
    [string]$VenvDir = ".venv",
    [switch]$InstallDev
)

$ErrorActionPreference = "Stop"

function Get-PythonLauncher {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return @("py", "-3")
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return @("python")
    }
    throw "Python 3 was not found in PATH."
}

$pythonLauncher = Get-PythonLauncher

Write-Host "Creating virtual environment in $VenvDir"
if ($pythonLauncher.Length -gt 1) {
    & $pythonLauncher[0] $pythonLauncher[1] -m venv $VenvDir
} else {
    & $pythonLauncher[0] -m venv $VenvDir
}

$pythonExe = Join-Path $VenvDir "Scripts\python.exe"

Write-Host "Upgrading pip"
& $pythonExe -m pip install --upgrade pip

if ($InstallDev) {
    Write-Host "Installing project with dev dependencies"
    & $pythonExe -m pip install -e ".[dev]"
} else {
    Write-Host "Installing project"
    & $pythonExe -m pip install -e .
}

Write-Host "Installing Playwright Chromium"
& $pythonExe -m playwright install chromium

Write-Host ""
Write-Host "Bootstrap complete."
Write-Host "Activate the venv with:"
Write-Host "  .\$VenvDir\Scripts\Activate.ps1"
Write-Host "Run one refresh with:"
Write-Host "  himawari-wallpaper --once"
