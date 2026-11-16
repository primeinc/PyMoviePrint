# Download and stage the exact, licensed FFmpeg distribution for the frozen app.
# Invocation: powershell.exe -NoProfile -File windows/Prepare-FFmpeg.ps1
[CmdletBinding()]
param(
    [string]$Destination = ''
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$Pin = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'ffmpeg-runtime.lock.json') -Raw | ConvertFrom-Json
if ($Pin.sha256 -notmatch '^[0-9a-f]{64}$') { throw 'Invalid pinned FFmpeg digest' }
if (-not $Destination) { $Destination = Join-Path $Repo 'dist/PyMoviePrint/ffmpeg' }
$Url = 'https://github.com/' + $Pin.publisher + '/releases/download/' + $Pin.release_tag + '/' + $Pin.asset
$Work = Join-Path $env:TEMP ('pymovieprint-ffmpeg-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $Work -Force | Out-Null
try {
    $Archive = Join-Path $Work $Pin.asset
    Invoke-WebRequest -Uri $Url -OutFile $Archive -MaximumRedirection 10
    $Actual = (Get-FileHash -LiteralPath $Archive -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($Actual -cne $Pin.sha256) { throw "FFmpeg asset digest mismatch: $Actual (expected $($Pin.sha256))" }
    $Expanded = Join-Path $Work 'expanded'
    Expand-Archive -LiteralPath $Archive -DestinationPath $Expanded -Force
    $FFmpeg = Get-ChildItem -LiteralPath $Expanded -Filter ffmpeg.exe -File -Recurse |
              Where-Object { $_.Directory.Name -eq 'bin' } | Select-Object -First 1
    if (-not $FFmpeg) { throw 'FFmpeg archive missing bin/ffmpeg.exe' }
    $Bin = $FFmpeg.DirectoryName
    if (-not (Test-Path -LiteralPath (Join-Path $Bin 'ffprobe.exe'))) {
        throw 'FFmpeg archive missing bin/ffprobe.exe'
    }
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    Copy-Item -Path (Join-Path $Bin '*') -Destination $Destination -Recurse -Force
    $LicenceDir = Join-Path $Destination 'licenses'
    New-Item -ItemType Directory -Path $LicenceDir -Force | Out-Null
    $Root = Split-Path -Parent $Bin
    foreach ($File in @(Get-ChildItem -LiteralPath $Root -File -ErrorAction SilentlyContinue)) {
        if ($File.Name -match '^(README|LICENSE|COPYING|CREDITS|NOTICE)') {
            Copy-Item -LiteralPath $File.FullName -Destination $LicenceDir -Force
        }
    }
    $Notice = @(
        'This installation includes FFmpeg, LGPL shared build; unmodified distributor binaries.'
        ('Release: https://github.com/' + $Pin.publisher + '/releases/tag/' + $Pin.release_tag)
        ('Asset: ' + $Pin.asset)
        ('SHA-256: ' + $Actual)
        ('Build recipes: https://github.com/' + $Pin.publisher + '/tree/' + $Pin.release_commit)
        ('Corresponding FFmpeg source: https://github.com/FFmpeg/FFmpeg/tree/' + $Pin.ffmpeg_source_commit)
        'FFmpeg licensing and source compliance: https://ffmpeg.org/legal.html'
        'Additional third-party component notices: included license files and build recipes.'
    )
    $Notice | Set-Content -LiteralPath (Join-Path $LicenceDir 'PROVENANCE.txt') -Encoding UTF8
    $VersionOutput = & (Join-Path $Destination 'ffmpeg.exe') -version
    if ($LASTEXITCODE -ne 0) { throw 'Bundled ffmpeg.exe failed to start' }
    if (($VersionOutput -join ' ') -match '--enable-(gpl|nonfree)') { throw 'Unexpected GPL/nonfree FFmpeg configuration' }
    & (Join-Path $Destination 'ffprobe.exe') -version | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Bundled ffprobe.exe failed to start' }
    $Receipt = [ordered]@{
        publisher = $Pin.publisher
        release_tag = $Pin.release_tag
        release_commit = $Pin.release_commit
        archive = $Pin.asset
        sha256 = $Actual
        ffmpeg_source_commit = $Pin.ffmpeg_source_commit
        ffmpeg_exe_sha256 = (Get-FileHash -LiteralPath (Join-Path $Destination 'ffmpeg.exe') -Algorithm SHA256).Hash.ToLowerInvariant()
        ffprobe_exe_sha256 = (Get-FileHash -LiteralPath (Join-Path $Destination 'ffprobe.exe') -Algorithm SHA256).Hash.ToLowerInvariant()
    }
    $Receipt | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Destination 'PROVENANCE.json') -Encoding UTF8
    Write-Host "Verified LGPL FFmpeg runtime $($Pin.release_tag): $Actual"
} finally {
    Remove-Item -LiteralPath $Work -Recurse -Force -ErrorAction SilentlyContinue
}
