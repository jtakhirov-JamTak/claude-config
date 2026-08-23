# Copy the versioned PowerShell profile into place.
#
#   ~/.claude/powershell-profile.ps1   source of truth, tracked in git
#   $PROFILE                            live file PowerShell actually loads
#
# A copy, deliberately, not a symlink: symlinks on Windows need elevation or
# developer mode, and OneDrive does not sync them reliably. The cost is that
# this has to be re-run after editing the source.
#
# Usage:  .\sync-profile.ps1          copy source -> $PROFILE
#         .\sync-profile.ps1 -Check   report drift, change nothing

[CmdletBinding()]
param([switch]$Check)

$ErrorActionPreference = 'Stop'

$source = Join-Path $PSScriptRoot 'powershell-profile.ps1'
if (-not (Test-Path $source)) {
    Write-Host "FAILED: source not found at $source" -ForegroundColor Red
    exit 1
}

Write-Host "source : $source"
Write-Host "target : $PROFILE"
Write-Host ''

$targetDir = Split-Path $PROFILE
if (-not (Test-Path $targetDir)) {
    if ($Check) {
        Write-Host 'DRIFT: profile directory does not exist.' -ForegroundColor Yellow
        exit 1
    }
    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    Write-Host "created $targetDir"
}

$identical = $false
if (Test-Path $PROFILE) {
    $identical = -not (Compare-Object (Get-Content $source) (Get-Content $PROFILE))
}

if ($identical) {
    Write-Host 'In sync — nothing to do.' -ForegroundColor Green
    exit 0
}

if ($Check) {
    if (Test-Path $PROFILE) {
        Write-Host 'DRIFT: live profile differs from the versioned copy.' -ForegroundColor Yellow
        Write-Host 'Diff (< versioned, > live):'
        Compare-Object (Get-Content $source) (Get-Content $PROFILE) |
            ForEach-Object { "  $($_.SideIndicator) $($_.InputObject)" }
    } else {
        Write-Host 'DRIFT: no live profile installed.' -ForegroundColor Yellow
    }
    exit 1
}

# Back up anything already there. Never overwrite an unseen file silently — the
# live copy may hold edits that were never folded back into the versioned one.
if (Test-Path $PROFILE) {
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $backup = "$PROFILE.bak-$stamp"
    Copy-Item $PROFILE $backup
    Write-Host "backed up existing profile -> $backup" -ForegroundColor Yellow
    Write-Host 'If it held edits you wanted, fold them into powershell-profile.ps1'
    Write-Host 'and re-run — the backup is not loaded by anything.'
    Write-Host ''
}

Copy-Item $source $PROFILE -Force

if (Compare-Object (Get-Content $source) (Get-Content $PROFILE)) {
    Write-Host 'FAILED: copy did not match the source.' -ForegroundColor Red
    exit 1
}

Write-Host 'Installed and verified identical.' -ForegroundColor Green
Write-Host 'Open a new terminal to load it.'
