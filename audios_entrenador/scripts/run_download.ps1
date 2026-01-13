\
$EnvFile = ".env"
if (Test-Path $EnvFile) {
  Get-Content $EnvFile | ForEach-Object {
    if ($_ -match "^\s*#") { return }
    if ($_ -match "^\s*$") { return }
    $kv = $_ -split "=", 2
    if ($kv.Length -eq 2) { [System.Environment]::SetEnvironmentVariable($kv[0].Trim(), $kv[1].Trim()) }
  }
}
python src\download_audios.py --out-dir $env:AUDIO_DIR --from $env:META_DESDE --to $env:META_HASTA_EXC
