\
# Ejecuta el evaluador cargando variables desde .env si existe
$EnvFile = ".env"
if (Test-Path $EnvFile) {
  Get-Content $EnvFile | ForEach-Object {
    if ($_ -match "^\s*#") { return }
    if ($_ -match "^\s*$") { return }
    $kv = $_ -split "=", 2
    if ($kv.Length -eq 2) {
      [System.Environment]::SetEnvironmentVariable($kv[0].Trim(), $kv[1].Trim())
    }
  }
  Write-Host "✅ Variables cargadas desde .env"
}

python src\eval_chats.py --input $env:INPUT_SRC --output $env:OUTPUT_PATH
