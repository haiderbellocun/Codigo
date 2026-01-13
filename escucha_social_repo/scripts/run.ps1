\
# Ejecutar con .env (PowerShell)
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
python src\escucha_social.py --input $env:INPUT_PATH --export $env:EXPORT_XLSX
