# Optional: Pfad zum Zielordner
$targetDir = "$HOME\napari"

# Ordner erstellen und hinein-navigieren
New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
Set-Location $targetDir

# venv erstellen
uv venv
Write-Host "`nVirtual environment was created."
# Aktivieren
Write-Host "Opening new terminal inside virtual environment ..."

Write-Host "`nexecute this command in the newly opened PowerShell:"
Write-Host "uv add oct-analysis" -ForegroundColor Cyan

Write-Host "`nAfter that: Done! Ready to use the napari plugin now."
Write-Host "To start napari, simply type " -NoNewline
Write-Host "napari" -ForegroundColor Yellow -NoNewline
Write-Host " while in the activated virtual environment."
Write-Host "Activate the environemt with " -NoNewline
Write-Host ".\.venv\Scripts\activate.ps1" -ForegroundColor Red -NoNewline
Write-Host " while in the napari-folder in Powershell."

Write-Host "`n You can close this terminal now."

Start-Process Powershell -ArgumentList "-NoExit", "-Command", ". .\.venv\Scripts\activate.ps1"