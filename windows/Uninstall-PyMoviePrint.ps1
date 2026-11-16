# Remove only this per-user PyMoviePrint Explorer installation.
[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Dest = Join-Path $env:LOCALAPPDATA 'Programs\PyMoviePrint'
$Marker = Join-Path $Dest '.pymovieprint-explorer.json'
if (-not (Test-Path -LiteralPath $Marker)) { throw 'No managed PyMoviePrint installation found' }
$verb = 'PyMoviePrint.ContactSheet'
foreach ($ext in @('.mp4', '.mkv', '.mov', '.avi', '.wmv', '.flv')) {
    $path = "Software\Classes\SystemFileAssociations\$ext\shell\$verb"
    $key = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey($path)
    if (-not $key) { continue }
    try {
        $command = $key.OpenSubKey('command')
        $cmd = if ($command) { try { [string]$command.GetValue('') } finally { $command.Close() } } else { '' }
        if ($cmd.IndexOf($Dest, [StringComparison]::OrdinalIgnoreCase) -lt 0) {
            throw "Explorer verb for $ext is not ours. Refusing removal."
        }
    } finally { $key.Close() }
    [Microsoft.Win32.Registry]::CurrentUser.DeleteSubKeyTree($path, $false)
}
$path = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\PyMoviePrintExplorer'
$key = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey($path)
if ($key) { $key.Close(); [Microsoft.Win32.Registry]::CurrentUser.DeleteSubKeyTree($path, $false) }
Remove-Item -LiteralPath $Dest -Recurse -Force
Write-Host 'Uninstalled PyMoviePrint Explorer integration. Your personal settings were preserved.'
