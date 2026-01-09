\
# Abre Chrome con Remote Debugging para que Selenium se conecte sin re-login constante.
$Chrome = "$env:ProgramFiles\Google\Chrome\Application\chrome.exe"
if (!(Test-Path $Chrome)) {
  $Chrome = "$env:ProgramFiles(x86)\Google\Chrome\Application\chrome.exe"
}
$Port = 9222
$ProfileDir = "C:\selenium\chrome-profile"

New-Item -ItemType Directory -Force -Path $ProfileDir | Out-Null

Start-Process -FilePath $Chrome -ArgumentList @(
  "--remote-debugging-port=$Port",
  "--user-data-dir=$ProfileDir",
  "--disable-popup-blocking",
  "--no-first-run"
)

Write-Host "✅ Chrome iniciado en DevTools: 127.0.0.1:$Port"
Write-Host "👉 Inicia sesión y deja el navegador abierto."
