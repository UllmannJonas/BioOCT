# Optional: Pfad zum Zielordner
$targetDir = "$HOME\napari"

# Ordner erstellen und hinein-navigieren
New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
Set-Location $targetDir

# venv erstellen
uv venv
Write-Host "_____________________________________________________________________"
Write-Host "`nVirtual environment was created."

# Anleitung
Write-Host "`nExecute these steps:"
Write-Host "1) Activate the environemt with " -NoNewline
Write-Host ".\.venv\Scripts\activate.ps1" -ForegroundColor Red -NoNewline
Write-Host " while in the napari-folder in Powershell.`n"

Write-Host "2) install the package via uv: " -NoNewline
Write-Host "uv pip install oct-analysis`n" -ForegroundColor Cyan

Write-Host "After that: Done! Ready to use the napari plugin now."
Write-Host "To start napari, simply type " -NoNewline
Write-Host "napari" -ForegroundColor Yellow -NoNewline
Write-Host " while in the activated virtual environment."

Write-Host "`n You can close this terminal now."
Write-Host "_____________________________________________________________________"