$root = Split-Path -Parent $PSScriptRoot
$apiCmd = ". '$root\\.venv\\Scripts\\Activate.ps1'; Set-Location '$root'; uvicorn apps.api.main:app --reload --port 8000"
$uiCmd = ". '$root\\.venv\\Scripts\\Activate.ps1'; Set-Location '$root'; streamlit run apps/dashboard/streamlit_app.py"

Start-Process powershell -ArgumentList @('-NoExit','-Command', $apiCmd)
Start-Process powershell -ArgumentList @('-NoExit','-Command', $uiCmd)

Write-Output 'Launched API and dashboard in separate PowerShell windows.'
Write-Output 'API docs: http://127.0.0.1:8000/docs'
Write-Output 'Dashboard: http://127.0.0.1:8501'
