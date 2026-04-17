param(
    [ValidateSet("conda", "venv")]
    [string]$Manager = "conda",
    [string]$VenvDir = ".venv",
    [switch]$InstallDev,
    [switch]$UseConda,
    [switch]$UseVenv,
    [string]$CondaEnvName = "himawari-wallpaper",
    [string]$PythonVersion = "3.11",
    [switch]$SkipPlaywright
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
$scriptArgs = @("scripts/bootstrap.py")

$resolvedManager = $Manager
if ($UseConda) {
    $resolvedManager = "conda"
}
if ($UseVenv) {
    $resolvedManager = "venv"
}

if ($resolvedManager -eq "conda") {
    $scriptArgs += @("--manager", "conda", "--conda-env-name", $CondaEnvName, "--python-version", $PythonVersion)
} else {
    $scriptArgs += @("--manager", "venv", "--venv", $VenvDir)
}

if ($InstallDev) {
    $scriptArgs += "--dev"
}

if ($SkipPlaywright) {
    $scriptArgs += "--skip-playwright"
}

if ($pythonLauncher.Length -gt 1) {
    & $pythonLauncher[0] $pythonLauncher[1] @scriptArgs
} else {
    & $pythonLauncher[0] @scriptArgs
}
