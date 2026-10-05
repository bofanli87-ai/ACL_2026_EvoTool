$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Endpoint = "http://127.0.0.1:11434/v1/models"

if (-not (Test-Path -LiteralPath $Python)) {
    throw ".venv not found. Run: py -3.13 -m venv .venv"
}

Write-Host "[1/3] Python environment"
& $Python --version
& $Python -c "import openai, yaml; print('openai=' + openai.__version__ + ', pyyaml=' + yaml.__version__)"

Write-Host "[2/3] Offline pipeline"
& $Python (Join-Path $RepoRoot "scripts\offline_smoke.py")
if ($LASTEXITCODE -ne 0) { throw "Offline smoke test failed" }

Write-Host "[3/3] Ollama OpenAI-compatible endpoint"
try {
    $Models = Invoke-RestMethod -Uri $Endpoint -Method Get -TimeoutSec 5
    $Names = @($Models.data | ForEach-Object { $_.id })
    if ($Names -contains "evotool-qwen3:8b") {
        Write-Host "OK: evotool-qwen3:8b is available; EvoTool is ready to run."
    } else {
        Write-Warning "Ollama is reachable, but evotool-qwen3:8b is missing. Run: ollama pull qwen3:8b; ollama create evotool-qwen3:8b -f configs/Modelfile.qwen3-8b"
        if ($Names.Count -gt 0) { Write-Host ("Available models: " + ($Names -join ", ")) }
    }
} catch {
    Write-Warning "Cannot reach $Endpoint. Install/start Ollama first; the offline code check is unaffected."
}
