$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
& "$root\.venv\Scripts\Activate.ps1"
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
