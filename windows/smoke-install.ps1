# Windows runner acceptance: real Inno install, shell command, upgrade and uninstall.
[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$Setup = Join-Path $Repo 'dist/PyMoviePrint-Setup.exe'
$Dest = Join-Path $env:LOCALAPPDATA 'Programs/PyMoviePrint'
$Exe = Join-Path $Dest 'PyMoviePrint.exe'
$Exts = @('.mp4', '.mkv', '.mov', '.avi', '.wmv', '.flv')
$Root = [Microsoft.Win32.Registry]::CurrentUser

function Run-Setup([string[]]$Arguments) {
    $proc = Start-Process -FilePath $Setup -ArgumentList $Arguments -Wait -PassThru
    if ($proc.ExitCode -ne 0) { throw "Installer failed with code $($proc.ExitCode)" }
}

function Assert-Registered {
    if (-not (Test-Path -LiteralPath $Exe)) { throw 'Installed PyMoviePrint.exe missing' }
    $expected = '"' + $Exe + '" "%1"'
    foreach ($ext in $Exts) {
        $path = "Software\Classes\SystemFileAssociations\$ext\shell\PyMoviePrint.ContactSheet"
        $key = $Root.OpenSubKey($path)
        if (-not $key) { throw "Missing Explorer verb $ext" }
        try {
            if ($key.GetValue('MultiSelectModel') -ne 'Document') { throw "Wrong selection mode $ext" }
            $command = $key.OpenSubKey('command')
            if (-not $command) { throw "Missing command $ext" }
            try {
                if ($command.GetValue('') -cne $expected) { throw "Wrong command $ext" }
            } finally { $command.Close() }
        } finally { $key.Close() }
    }
}

function Assert-Bundled-FFmpeg {
    $Bin = Join-Path $Dest 'ffmpeg'
    foreach ($Name in @('ffmpeg.exe','ffprobe.exe','PROVENANCE.json')) {
        $Path = Join-Path $Bin $Name
        if (-not (Test-Path -LiteralPath $Path)) { throw "Bundled media runtime missing: $Path" }
    }
    $Manifest = Get-Content -LiteralPath (Join-Path $Bin 'PROVENANCE.json') -Raw | ConvertFrom-Json
    $Pin = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'ffmpeg-runtime.lock.json') -Raw | ConvertFrom-Json
    if ($Manifest.sha256 -cne $Pin.sha256) {
        throw 'Bundled FFmpeg does not match the committed runtime lock'
    }
    $Output = & (Join-Path $Bin 'ffmpeg.exe') -version
    if ($LASTEXITCODE -ne 0) { throw 'Bundled ffmpeg.exe cannot start' }
    if (($Output -join ' ') -match '--enable-(gpl|nonfree)') { throw 'Non-LGPL FFmpeg build bundled' }
    & (Join-Path $Bin 'ffprobe.exe') -version | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Bundled ffprobe.exe cannot start' }
    Write-Host 'Pinned FFmpeg runtime verified from installed application without PATH dependency.'
}

function Assert-ExplorerLaunch {
    $video = Join-Path $env:TEMP 'PyMoviePrint scene; selection.mp4'
    & ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'testsrc2=size=160x90:rate=4:duration=2' -c:v mpeg4 -q:v 6 -an $video 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $video)) { throw 'Could not generate real video test fixture' }

    $log = Join-Path $env:USERPROFILE '.pymovieprint\logs\pymovieprint.log'
    $previousLength = if (Test-Path -LiteralPath $log) { (Get-Item -LiteralPath $log).Length } else { 0 }
    $process = Start-Process -FilePath $video -Verb 'PyMoviePrint.ContactSheet' -PassThru
    if (-not $process) { throw 'ShellExecute did not return a GUI process for the registered Explorer verb' }
    try {
        $found = $false
    $imported = $false
    $previewed = $false
        $deadline = [DateTime]::UtcNow.AddSeconds(55)
        do {
            Start-Sleep -Milliseconds 600
            $process.Refresh()
            if ($process.HasExited) { throw "Frozen GUI exited before confirming video import, exit $($process.ExitCode)" }
            try {
                if (Test-Path -LiteralPath $log) {
                    $logInfo = Get-Item -LiteralPath $log
                    if ($logInfo.Length -gt $previousLength) {
                        $stream = [IO.File]::Open($log, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::ReadWrite)
                        try {
                            $stream.Seek($previousLength, [IO.SeekOrigin]::Begin) | Out-Null
                            $reader = New-Object IO.StreamReader($stream, [Text.Encoding]::UTF8)
                            $newText = $reader.ReadToEnd()
                            $reader.Dispose()
                        } finally { if ($stream) { $stream.Dispose() } }
                        if ($newText.Contains('Explorer source import confirmed: 1 video(s)')) { $imported = $true }
                        if ($newText -match 'Video contact sheet preview complete: .* frames=[1-9][0-9]* image=ready') { $previewed = $true }
                        if ($imported -and $previewed) { $found = $true; break }
                    }
                }
            } catch [IO.IOException] { }
        } while ([DateTime]::UtcNow -lt $deadline)
        if (-not $found) { throw 'GUI did not emit real video import and rendered-preview receipts' }
        Write-Host "Windows ShellExecute verb launched frozen GUI, imported and rendered contact-sheet preview for: $video"
    } finally {
        $process.Refresh()
        if (-not $process.HasExited) { Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue }
        Remove-Item -LiteralPath $video -Force -ErrorAction SilentlyContinue
    }
}

function Assert-Unregistered {
    foreach ($ext in $Exts) {
        $path = "Software\Classes\SystemFileAssociations\$ext\shell\PyMoviePrint.ContactSheet"
        $key = $Root.OpenSubKey($path)
        if ($key) { $key.Close(); throw "Explorer verb $ext survived uninstall" }
    }
    if (Test-Path -LiteralPath $Exe) { throw 'Application executable survived uninstall' }
}

function Find-Uninstaller {
    $found = @(Get-ChildItem -LiteralPath $Dest -File -Filter 'unins*.exe' -ErrorAction Stop)
    if ($found.Count -ne 1) { throw "Expected one managed uninstaller; got $($found.Count)" }
    return $found[0].FullName
}

function Uninstall-Managed {
    $uninstaller = Find-Uninstaller
    $proc = Start-Process -FilePath $uninstaller -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART') -Wait -PassThru
    if ($proc.ExitCode -ne 0) { throw "Uninstall failed with code $($proc.ExitCode)" }
}

if (-not (Test-Path $Setup)) { throw 'Missing setup installer' }
Run-Setup @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', "/LOG=$PSScriptRoot/install.log")
Assert-Registered
Assert-Bundled-FFmpeg
Assert-ExplorerLaunch
Run-Setup @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', "/LOG=$PSScriptRoot/upgrade.log")
Assert-Registered
Assert-Bundled-FFmpeg

# Fault injection: a foreign edit to an owned verb must block an update BEFORE any file change.
$path = 'Software\Classes\SystemFileAssociations\.mkv\shell\PyMoviePrint.ContactSheet'
$key = $Root.OpenSubKey($path, $true)
if (-not $key) { throw 'Cannot inject registry conflict' }
try { $key.SetValue('MUIVerb', 'A foreign editor') } finally { $key.Close() }
$bad = Start-Process -FilePath $Setup -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART') -Wait -PassThru
if ($bad.ExitCode -eq 0) { throw 'Installer overwrote changed Explorer association' }
if (-not (Test-Path $Exe)) { throw 'Previous installation was removed on preflight failure' }
$key = $Root.OpenSubKey($path, $true)
try { $key.SetValue('MUIVerb', 'Create video contact sheet') } finally { $key.Close() }
Assert-Registered

# Ownership test: uninstall must preserve a command replaced by another program.
$replacedPath = $path + '\command'
$changed = $Root.OpenSubKey($replacedPath, $true)
try { $changed.SetValue('', '"C:\Foreign\viewer.exe" "%1"') } finally { $changed.Close() }
Uninstall-Managed
$key = $Root.OpenSubKey($replacedPath)
if (-not $key) { throw 'Uninstall deleted foreign command' }
try {
    if ($key.GetValue('') -cne '"C:\Foreign\viewer.exe" "%1"') { throw 'Foreign command changed during uninstall' }
} finally { $key.Close() }
$Root.DeleteSubKeyTree($path, $false)
Assert-Unregistered
Write-Host 'Windows installer lifecycle passed: install, upgrade, conflict, foreign verb, uninstall.'
