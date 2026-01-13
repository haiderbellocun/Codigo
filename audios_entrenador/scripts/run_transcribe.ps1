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
python src\transcribe_audios.py --audio-dir $env:AUDIO_DIR --out-dir $env:TRANSCRIPTS_DIR
