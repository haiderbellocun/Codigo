\
# Ejecuta el scraper cargando variables desde .env si existe
# Nota: PowerShell no carga .env nativamente; este script hace una carga simple KEY=VALUE

$EnvFile = ".env"
if (Test-Path $EnvFile) {
  Get-Content $EnvFile | ForEach-Object {
    if ($_ -match "^\s*#") { return }
    if ($_ -match "^\s*$") { return }
    $kv = $_ -split "=", 2
    if ($kv.Length -eq 2) {
      $name = $kv[0].Trim()
      $value = $kv[1].Trim()
      [System.Environment]::SetEnvironmentVariable($name, $value)
    }
  }
  Write-Host "✅ Variables cargadas desde .env"
}

python src\scraper.py
