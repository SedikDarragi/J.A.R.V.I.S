# One-time setup for J.A.R.V.I.S. on a fresh machine.
# Downloads: Python dependencies, Piper voice, Ollama runtime + AI model.
# Run with:  powershell -ExecutionPolicy Bypass -File setup.ps1

$ErrorActionPreference = "Stop"
$Here = $PSScriptRoot
$VoiceUrl = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/alan/medium/en_GB-alan-medium.onnx"
$VoiceJsonUrl = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/alan/medium/en_GB-alan-medium.onnx.json"
$OllamaZipUrl = "https://github.com/ollama/ollama/releases/latest/download/ollama-windows-amd64.zip"
$Model = "llama3.2:3b"

Write-Host "[1/4] Installing Python dependencies..." -ForegroundColor Cyan
pip install -r "$Here\requirements.txt"
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

Write-Host "[2/4] Downloading JARVIS voice..." -ForegroundColor Cyan
$VoiceDir = "$Here\voices"
New-Item -ItemType Directory -Path $VoiceDir -Force | Out-Null
if (-not (Test-Path "$VoiceDir\en_GB-alan-medium.onnx")) {
    Invoke-WebRequest -Uri $VoiceUrl -OutFile "$VoiceDir\en_GB-alan-medium.onnx" -UseBasicParsing
    Invoke-WebRequest -Uri $VoiceJsonUrl -OutFile "$VoiceDir\en_GB-alan-medium.onnx.json" -UseBasicParsing
    Write-Host "    voice downloaded."
} else {
    Write-Host "    voice already present."
}

Write-Host "[3/4] Installing Ollama runtime..." -ForegroundColor Cyan
if (-not (Test-Path "$Here\ollama\ollama.exe")) {
    $Zip = "$env:TEMP\ollama-windows-amd64.zip"
    if (-not (Test-Path $Zip)) {
        Write-Host "    downloading Ollama (~1.4 GB, this takes a while)..."
        Invoke-WebRequest -Uri $OllamaZipUrl -OutFile $Zip -UseBasicParsing
    }
    Expand-Archive -Path $Zip -DestinationPath "$Here\ollama" -Force
    Write-Host "    Ollama extracted."
} else {
    Write-Host "    Ollama already present."
}

Write-Host "[4/4] Pulling AI model ($Model)..." -ForegroundColor Cyan
$ollamaExe = "$Here\ollama\ollama.exe"
$already = try { (& $ollamaExe list 2>$null) -ne $null } catch { $false }
if (-not $already) {
    Start-Process -FilePath $ollamaExe -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 5
}
& $ollamaExe pull $Model
if ($LASTEXITCODE -ne 0) { throw "model pull failed" }

Write-Host ""
Write-Host "Setup complete. Create your config:  Copy-Item config.example.json config.json" -ForegroundColor Green
Write-Host "Then start Jarvis with:  .\start_jarvis.bat" -ForegroundColor Green
