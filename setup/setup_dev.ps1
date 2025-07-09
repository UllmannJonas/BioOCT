# Optional: Pfad zum Zielordner
$targetDir = "$HOME\oct-analysis"
$repoUrl = "https://github.com/AndreasNetsch/oct_analysis.git"
$packageName = "oct-analysis"

# github repo oct-analysis klonen
if (-not (Test-Path $targetDir)) {
    Write-Host "⬇️ Klone Repository $packageName ..."
    git clone $repoUrl $targetDir
} else {
    Write-Host "📁 Ordner '$targetDir' existiert bereits. Skipping clone."
}

# In neuen Ordner navigieren
Set-Location $targetDir

# venv erstellen
uv venv
Write-Host "`nVirtual environment was created."
# venv aktivieren
Write-Host "Opening new terminal inside virtual environment ...`n"

Write-Host "Execute this command in the newly opened PowerShell:"
Write-Host "uv sync" -ForegroundColor Cyan

Write-Host "`nAfter that: Done! Ready to work on the project now."
Write-Host "Don't forget to create a branch when making changes ;)." -ForegroundColor Red
Write-Host "Look for guidance in oct-analysis/docs/collab_workflow.md" -ForegroundColor Red

Write-Host "`nYou can close this terminal now."
Start-Process pwsh -ArgumentList "-NoExit", "-Command", ". .\.venv\Scripts\activate.ps1"