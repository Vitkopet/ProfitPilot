# ProfitPilot Windows local installer. No live orders. Requires Windows PowerShell 5.1.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
try {
  if (-not [Environment]::Is64BitOperatingSystem) { throw 'Requires 64-bit Windows' }
  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
  $root = Join-Path $env:LOCALAPPDATA 'ProfitPilot'
  $app = Join-Path $root 'app'
  $tmp = Join-Path $env:TEMP ('profitpilot-' + [guid]::NewGuid().ToString('N'))
  foreach ($p in @($root,$tmp,(Join-Path $root 'reports'),(Join-Path $root 'history'),(Join-Path $root 'logs'))) {
    New-Item -ItemType Directory -Path $p -Force | Out-Null
  }
  $python = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'
  if (-not (Test-Path $python)) {
    Write-Host 'Downloading Python 3.12 from python.org...'
    $installer = Join-Path $tmp 'python.exe'
    Invoke-WebRequest 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe' -OutFile $installer -UseBasicParsing
    if ((Get-AuthenticodeSignature $installer).Status -ne 'Valid') { throw 'Invalid Python installer signature' }
    $p = Start-Process $installer -ArgumentList '/quiet InstallAllUsers=0 Include_pip=0 Include_test=0 Include_launcher=0 PrependPath=0 Shortcuts=0' -Wait -PassThru
    if ($p.ExitCode -ne 0) { throw "Python install error: $($p.ExitCode)" }
  }
  if (-not (Test-Path $python)) { throw 'Python 3.12 not found after installation' }
  Write-Host 'Downloading ProfitPilot from GitHub...'
  $zip = Join-Path $tmp 'source.zip'
  Invoke-WebRequest 'https://github.com/Vitkopet/ProfitPilot/archive/refs/heads/main.zip' -OutFile $zip -UseBasicParsing
  Expand-Archive $zip -DestinationPath $tmp -Force
  $source = Join-Path $tmp 'ProfitPilot-main'
  if (-not (Test-Path (Join-Path $source 'acceleration.py'))) { throw 'Scanner source not found' }
  Push-Location $source
  try {
    & $python -m unittest -v
    if ($LASTEXITCODE -ne 0) { throw 'Unit tests failed' }
  } finally { Pop-Location }
  if (Test-Path $app) {
    Move-Item $app (Join-Path $root ('app-backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss')))
  }
  Copy-Item $source $app -Recurse
  $runner = Join-Path $root 'Run-ProfitPilot.ps1'
  @'
$ErrorActionPreference = 'Stop'
$root = Join-Path $env:LOCALAPPDATA 'ProfitPilot'
$mutex = New-Object System.Threading.Mutex($false, 'Local\ProfitPilotScanner5Min')
$locked = $false
try {
  $locked = $mutex.WaitOne(0)
  if (-not $locked) { return }
  $stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
  $log = Join-Path $root "logs\scan-$stamp.log"
  $report = Join-Path $root 'reports'
  $started = (Get-Date).ToUniversalTime()
  Push-Location (Join-Path $root 'app')
  try {
    & (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe') 'acceleration.py' '--limit' '50' '--output' $report *> $log
    $code = $LASTEXITCODE
  } finally { Pop-Location }
  $latest = Join-Path $report 'latest.json'
  if ((Test-Path $latest) -and (Get-Item $latest).LastWriteTimeUtc -ge $started) {
    Copy-Item $latest (Join-Path $root "history\report-$stamp.json")
  }
  if ($code -ne 0) { "Scanner exit code: $code" | Add-Content $log }
} catch {
  ($_ | Out-String) | Add-Content (Join-Path $root 'logs\runner-errors.log')
} finally {
  if ($locked) { $mutex.ReleaseMutex() }
  $mutex.Dispose()
}
'@ | Set-Content $runner -Encoding UTF8
  $action = New-ScheduledTaskAction -Execute (Join-Path $PSHOME 'powershell.exe') -Argument ('-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $runner + '"')
  $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 5)
  $principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
  $settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 4) -StartWhenAvailable
  Register-ScheduledTask -TaskName 'ProfitPilot Scanner Every 5 Minutes' -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
  Write-Host 'Running first scan (1-3 minutes)...'
  & (Join-Path $PSHOME 'powershell.exe') -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $runner
  Write-Host "DONE. Reports: $root\reports ; logs: $root\logs" -ForegroundColor Green
  Write-Host 'Runs every 5 minutes while signed in and PC is awake. Google Drive not configured.'
} catch {
  Write-Host ('INSTALL ERROR: ' + $_.Exception.Message) -ForegroundColor Red
} finally {
  if ($tmp -and (Test-Path $tmp)) { Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue }
  Read-Host 'Press Enter to close'
}
