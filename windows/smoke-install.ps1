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
Run-Setup @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', "/LOG=$PSScriptRoot/upgrade.log")
Assert-Registered

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
