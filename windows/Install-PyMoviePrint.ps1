# Installs this fork checkout as a per-user app with a Windows Explorer context-menu verb.
[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$Repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$Dest = Join-Path $env:LOCALAPPDATA 'Programs\PyMoviePrint'
$Marker = Join-Path $Dest '.pymovieprint-explorer.json'
$Backup = "$Dest.backup.$([guid]::NewGuid().ToString('N'))"
$Verb = 'PyMoviePrint.ContactSheet'
$Extensions = @('.mp4', '.mkv', '.mov', '.avi', '.wmv', '.flv')
$Old = $false
$New = $false

function Find-Python {
    $probe = 'import sys, tkinter; assert sys.version_info[:2] == (3, 11); print(sys.executable)'
    $local = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'
    foreach ($candidate in @($local, 'py.exe', 'python.exe')) {
        if (-not (Test-Path -LiteralPath $candidate) -and -not (Get-Command $candidate -ErrorAction SilentlyContinue)) { continue }
        try {
            if ($candidate -eq 'py.exe') { $out = & $candidate -3.11 -c $probe 2>$null }
            else { $out = & $candidate -c $probe 2>$null }
            if ($LASTEXITCODE -eq 0 -and $out) { return ([string](@($out)[-1])).Trim() }
        } catch {}
    }
    return $null
}
function Ensure-Python {
    $python = Find-Python
    if ($python) { return $python }
    if (-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) { throw 'Python 3.11 with Tkinter is required; install it or winget and rerun.' }
    & winget.exe install --exact --id Python.Python.3.11 --source winget --scope user --accept-package-agreements --accept-source-agreements --disable-interactivity
    if ($LASTEXITCODE -ne 0) { throw "Python install failed: $LASTEXITCODE" }
    $python = Find-Python
    if (-not $python) { throw 'Python 3.11 not found after installation. Open a new terminal and rerun.' }
    return $python
}
function Find-FFmpeg {
    $cmd = Get-Command ffmpeg.exe -ErrorAction SilentlyContinue
    if ($cmd) {
        $folder = Split-Path -Parent $cmd.Source
        if (Test-Path -LiteralPath (Join-Path $folder 'ffprobe.exe')) { return $folder }
    }
    foreach ($folder in @((Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages'), (Join-Path $env:ProgramFiles 'ffmpeg'), (Join-Path $env:ProgramFiles 'Gyan'))) {
        if (-not (Test-Path -LiteralPath $folder)) { continue }
        foreach ($exe in @(Get-ChildItem -LiteralPath $folder -Filter ffmpeg.exe -File -Recurse -ErrorAction SilentlyContinue)) {
            if (Test-Path -LiteralPath (Join-Path $exe.DirectoryName 'ffprobe.exe')) { return $exe.DirectoryName }
        }
    }
    return $null
}
function Ensure-FFmpeg {
    $bin = Find-FFmpeg
    if ($bin) { return $bin }
    if (-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) { throw 'Install FFmpeg and ffprobe, then rerun.' }
    & winget.exe install --exact --id Gyan.FFmpeg --source winget --accept-package-agreements --accept-source-agreements --disable-interactivity
    if ($LASTEXITCODE -ne 0) { throw "FFmpeg install failed: $LASTEXITCODE" }
    $bin = Find-FFmpeg
    if (-not $bin) { throw 'FFmpeg not found after installation. Restart terminal and rerun.' }
    return $bin
}

function Add-ShellMenu($pythonw, $entry) {
    $cmd = '"' + $pythonw + '" "' + $entry + '" "%1"'
    foreach ($ext in $Extensions) {
        $path = "Software\Classes\SystemFileAssociations\$ext\shell\$Verb"
        $key = [Microsoft.Win32.Registry]::CurrentUser.CreateSubKey($path)
        try {
            $key.SetValue('MUIVerb', 'Create video contact sheet')
            $key.SetValue('MultiSelectModel', 'Single')
            $child = $key.CreateSubKey('command')
            try { $child.SetValue('', $cmd) } finally { $child.Close() }
        } finally { $key.Close() }
        $check = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey("$path\command")
        try { if (-not $check -or [string]$check.GetValue('') -cne $cmd) { throw "Failed to verify Explorer verb $ext" } }
        finally { if ($check) { $check.Close() } }
    }
}
function Add-Uninstaller {
    $key = [Microsoft.Win32.Registry]::CurrentUser.CreateSubKey('Software\Microsoft\Windows\CurrentVersion\Uninstall\PyMoviePrintExplorer')
    try {
        $script = Join-Path $Dest 'Uninstall-PyMoviePrint.ps1'
        $key.SetValue('DisplayName', 'PyMoviePrint with Explorer integration')
        $key.SetValue('Publisher', 'primeinc/PyMoviePrint')
        $key.SetValue('DisplayVersion', '1.1.0.1')
        $key.SetValue('InstallLocation', $Dest)
        $key.SetValue('UninstallString', ('powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' + $script + '"'))
    } finally { $key.Close() }
}

try {
    $files = @('movieprint_gui.py', 'movieprint_maker.py', 'video_processing.py',
               'image_grid.py', 'state_manager.py', 'project_io.py', 'workspace_tools.py',
               'face_analysis.py', 'version.py', 'requirements.txt', 'shell_entry.py')
    foreach ($file in $files) {
        if (-not (Test-Path -LiteralPath (Join-Path $Repo $file))) { throw "Incomplete fork checkout: missing $file" }
    }
    if (-not (Test-Path -LiteralPath (Join-Path $Repo 'assets'))) { throw 'Missing assets folder' }
    if ((Test-Path -LiteralPath $Dest) -and -not (Test-Path -LiteralPath $Marker)) {
        throw "Destination $Dest is not a managed installation; refusing overwrite."
    }
    if (-not (Test-Path -LiteralPath $Marker)) {
        foreach ($ext in $Extensions) {
            $path = "Software\Classes\SystemFileAssociations\$ext\shell\$Verb"
            $key = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey($path)
            if ($key) { $key.Close(); throw "Explorer verb $ext already owned by another installation" }
        }
    }
    $python = Ensure-Python
    if (Test-Path -LiteralPath $Dest) { Move-Item -LiteralPath $Dest -Destination $Backup; $Old = $true }
    New-Item -ItemType Directory -Path $Dest -Force | Out-Null
    $New = $true
    foreach ($file in $files) {
        Copy-Item -LiteralPath (Join-Path $Repo $file) -Destination (Join-Path $Dest $file) -Force
    }
    Copy-Item -LiteralPath (Join-Path $Repo 'assets') -Destination (Join-Path $Dest 'assets') -Recurse -Force
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'Uninstall-PyMoviePrint.ps1') -Destination $Dest -Force

    & $python -m venv (Join-Path $Dest '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Failed to initialize Python virtual environment' }
    $py = Join-Path $Dest '.venv\Scripts\python.exe'
    $pythonw = Join-Path $Dest '.venv\Scripts\pythonw.exe'
    if (-not (Test-Path -LiteralPath $pythonw)) { throw 'Missing venv pythonw.exe' }
    & $py -m pip install --disable-pip-version-check -r (Join-Path $Dest 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
    & $py -c 'import tkinter, cv2, PIL, customtkinter, scenedetect'
    if ($LASTEXITCODE -ne 0) { throw 'PyMoviePrint dependencies cannot be imported' }
    $bin = Ensure-FFmpeg
    Set-Content -LiteralPath (Join-Path $Dest 'ffmpeg-bin.txt') -Encoding UTF8 -Value $bin
    @{ source='primeinc/PyMoviePrint'; installed_utc=[DateTime]::UtcNow.ToString('o') } |
        ConvertTo-Json | Set-Content -LiteralPath $Marker -Encoding UTF8
    Add-ShellMenu $pythonw (Join-Path $Dest 'shell_entry.py')
    Add-Uninstaller
    if ($Old) { Remove-Item -LiteralPath $Backup -Recurse -Force }
    Write-Host 'Installed: right-click video > Show more options > Create video contact sheet'
} catch {
    [Console]::Error.WriteLine("INSTALL FAILED: $($_.Exception.Message)")
    if ($New -and -not $Old) {
        foreach ($ext in $Extensions) {
            $path = "Software\Classes\SystemFileAssociations\$ext\shell\$Verb"
            $key = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey($path)
            if ($key) { $key.Close(); [Microsoft.Win32.Registry]::CurrentUser.DeleteSubKeyTree($path, $false) }
        }
        $path = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\PyMoviePrintExplorer'
        $key = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey($path)
        if ($key) { $key.Close(); [Microsoft.Win32.Registry]::CurrentUser.DeleteSubKeyTree($path, $false) }
    }
    if ($New -and (Test-Path -LiteralPath $Dest)) {
        Remove-Item -LiteralPath $Dest -Recurse -Force -ErrorAction SilentlyContinue
    }
    if ($Old -and (Test-Path -LiteralPath $Backup)) {
        Move-Item -LiteralPath $Backup -Destination $Dest -ErrorAction SilentlyContinue
    }
    exit 1
}
