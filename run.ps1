# Launches Jarvis from the project virtual environment.
# Any arguments are passed straight through, e.g.  .\run.ps1 --text
Set-Location $PSScriptRoot

$python = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "No .venv found - run .\setup.ps1 first. Falling back to system Python." -ForegroundColor Yellow
    $python = "py"
}

& $python -m jarvis @args
