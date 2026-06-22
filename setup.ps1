# Creates a Python virtual environment and installs Jarvis dependencies.
# Usage:  .\setup.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "Creating virtual environment (.venv)..."
py -m venv .venv

$python = ".\.venv\Scripts\python.exe"
Write-Host "Upgrading pip and installing requirements..."
& $python -m pip install --upgrade pip
& $python -m pip install -r requirements.txt

Write-Host "Downloading wake-word models (Hey Jarvis)..."
& $python -c "from openwakeword.utils import download_models; download_models()"

Write-Host "Downloading speech-to-text model (base.en)..."
& $python -c "from faster_whisper import WhisperModel; WhisperModel('base.en', device='cpu', compute_type='int8')"

Write-Host ""
Write-Host "Python dependencies installed. Next steps:" -ForegroundColor Green
Write-Host "  1) Install Ollama:   winget install Ollama.Ollama"
Write-Host "  2) Pull a model:     ollama pull llama3.2:3b"
Write-Host "  3) Check the setup:  .\run.ps1 --doctor"
Write-Host "  4) Say 'Hey Jarvis': .\run.ps1"
