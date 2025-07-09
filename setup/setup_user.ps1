# Optional: Pfad zum Zielordner
$targetDir = "$HOME\napari"

# Ordner erstellen und hinein-navigieren
New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
Set-Location $targetDir

# venv erstellen
uv venv
Write-Host "`n Virtual environment was created.`n"

# Aktivieren
Write-Host "`n Opening new terminal inside virtual environment ..."

Write-Host "execute these commands in the newly opened PowerShell:"
Write-Host "First: pip install uv" -ForegroundColor Yellow
Write-Host "Second: uv add oct-analysis" -ForegroundColor Cyan

Write-Host "`n After that: Done! Ready to work on the project now.`n"
Write-Host "`n You can close this terminal now."

Start-Process powershell -ArgumentList "-NoExit", "-Command", ". .\.venv\Scripts\activate"