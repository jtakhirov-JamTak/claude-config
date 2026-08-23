# Canonical scaffold for a new app from agentic-template-v4.
#
# This file is the ONE definition of the scaffold. ~/.claude/commands/new-app.md
# delegates here rather than restating the steps, so there is nothing to keep in
# sync.
#
# Run it in your own terminal, then launch `claude` INSIDE the new folder.
# A session binds its project root at launch: project CLAUDE.md,
# .claude/settings.json and the three hooks all resolve against that root.
# `/cd` can rebind the root (documented), but whether hooks and permissions
# follow it is NOT documented — so a fresh launch inside the app is the safe
# call, not a mid-session cd.
#
# Usage:  .\new-app.ps1 my-app-name
#         .\new-app.ps1 my-app-name -Public
#         .\new-app.ps1 my-app-name -Root C:\somewhere\else

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Name,

    [string]$Root = 'C:\Users\jtakh\dev',

    [switch]$Public,

    # Scaffold only: leave you in the new folder without starting Claude.
    [switch]$NoLaunch
)

$ErrorActionPreference = 'Stop'
$TEMPLATE = 'jtakhirov-JamTak/agentic-template-v4'

function Fail($msg) {
    Write-Host ''
    Write-Host "FAILED: $msg" -ForegroundColor Red
    exit 1
}

function Step($n, $msg) {
    Write-Host ''
    Write-Host "[$n] $msg" -ForegroundColor Cyan
}

# --- Step 0: preflight -------------------------------------------------------
Step 0 'Preflight'

if ($Name -notmatch '^[A-Za-z0-9._-]+$') {
    Fail "'$Name' is not a usable repo name (letters, digits, . _ - only)."
}
if (-not (Test-Path $Root)) { Fail "Dev root '$Root' does not exist." }

$target = Join-Path $Root $Name
if (Test-Path $target) { Fail "'$target' already exists. Pick another name." }

# Never scaffold into the home directory itself — a session started there loads
# no project CLAUDE.md.
if ((Resolve-Path $Root).Path.TrimEnd('\') -eq 'C:\Users\jtakh') {
    Fail 'Refusing to scaffold into the home directory. Use a dev root.'
}

try { Get-Command gh -ErrorAction Stop | Out-Null } catch { Fail 'gh CLI not found on PATH.' }
try { Get-Command git -ErrorAction Stop | Out-Null } catch { Fail 'git not found on PATH.' }

gh repo view "jtakhirov-JamTak/$Name" 2>$null | Out-Null
if ($?) { Fail "A GitHub repo named '$Name' already exists." }

Write-Host "  name '$Name' is free locally and on GitHub"

# --- Step 1: create from the template ---------------------------------------
Step 1 'Creating repo from template'

Set-Location $Root
$visibility = if ($Public) { '--public' } else { '--private' }
if ($Public) { Write-Host '  WARNING: creating PUBLIC. Public is effectively irreversible once indexed.' -ForegroundColor Yellow }

gh repo create $Name --template $TEMPLATE $visibility --clone
if (-not $?) { Fail 'gh repo create failed.' }
if (-not (Test-Path $target)) { Fail 'Clone did not produce the expected directory.' }

Set-Location $target

# --- Step 2: point git at the template's hooks ------------------------------
Step 2 'Wiring .githooks'

git config core.hooksPath .githooks
if (-not $?) { Fail 'git config core.hooksPath failed.' }

$hp = git config --get core.hooksPath
if ($hp -ne '.githooks') { Fail "core.hooksPath reads back as '$hp', expected '.githooks'." }
Write-Host "  core.hooksPath = $hp"

# --- Step 3: make pre-commit executable -------------------------------------
Step 3 'Marking pre-commit executable'

# Windows git checks the file out non-executable and CI/WSL/macOS silently skip
# non-executable hooks.
git update-index --chmod=+x .githooks/pre-commit
if (-not $?) { Fail 'git update-index failed.' }

git commit -m 'chore: mark pre-commit hook executable'
if (-not $?) { Fail 'Commit of the mode change failed.' }

$mode = (git ls-files -s .githooks/pre-commit) -split '\s+' | Select-Object -First 1
if ($mode -ne '100755') { Fail "pre-commit mode is $mode, expected 100755." }
Write-Host "  pre-commit mode = $mode"

# --- Step 4: the interpreter the hooks call ---------------------------------
Step 4 'Checking the Python the hooks invoke'

# The three PreToolUse hooks invoke `python` by name. Hooks fail OPEN on their
# own errors by design, so a missing interpreter means the guardrails are
# silently decorative rather than loudly broken. This is the check that catches
# it.
$python = $null
try { $python = Get-Command python -ErrorAction Stop } catch { }

if ($python) {
    Write-Host "  $(python --version 2>&1)"
} else {
    $launcher = $null
    try { $launcher = Get-Command py -ErrorAction Stop } catch { }
    if (-not $launcher) {
        Fail 'Neither `python` nor `py` resolves. The hooks would fail open and the guardrails would be decorative. Install Python, then re-run.'
    }
    Write-Host '  `python` missing but `py` resolves — patching .claude/settings.json' -ForegroundColor Yellow
    $settings = '.claude/settings.json'
    $raw = Get-Content $settings -Raw
    $patched = $raw -replace '"command":\s*"python"', '"command": "py"'
    Set-Content -Path $settings -Value $patched -Encoding utf8 -NoNewline
    try { Get-Content $settings -Raw | ConvertFrom-Json | Out-Null } catch { Fail 'Patching settings.json produced invalid JSON. Restore it and fix by hand.' }
    $left = (Select-String -Path $settings -Pattern '"command": "python"' -AllMatches).Count
    if ($left -ne 0) { Fail "settings.json still has $left python entries." }
    Write-Host "  patched, JSON still valid ($(py --version 2>&1))"
    git add $settings
    git commit -m 'chore: point hooks at the py launcher'
}

# --- Done --------------------------------------------------------------------
# Everything below prints BEFORE Claude starts, because once it does it owns the
# terminal and anything written here scrolls away unread.
Write-Host ''
Write-Host '--- Scaffold ready ---------------------------------------------' -ForegroundColor Green
Write-Host "  $target"
Write-Host ''
Write-Host '  Verified: core.hooksPath, pre-commit mode 100755, interpreter resolves.'
Write-Host '  NOT verified (needs a live session): hook registration, permission rules.'
Write-Host '  That is what the canary below is for.'
Write-Host ''
Write-Host '  TWO THINGS ONLY YOU CAN DO:' -ForegroundColor Yellow
Write-Host ''
Write-Host '   1. Accept the trust dialog on first launch.' -ForegroundColor Yellow
Write-Host '      Decline it and no project hooks or permission rules load.'
Write-Host ''
Write-Host '   2. Send this as your first message:' -ForegroundColor Yellow
Write-Host '           read .env'
Write-Host '      It must be DENIED. If Claude reads it, the project settings did'
Write-Host '      not load - stop and fix that before building anything.'
Write-Host ''
Write-Host '  Then: Shift+Tab into Plan Mode, run  /interview <your app idea>'
Write-Host '----------------------------------------------------------------' -ForegroundColor Green
Write-Host ''

Set-Location $target

if ($NoLaunch) {
    Write-Host 'Scaffold only (-NoLaunch). Run `claude` here when ready.'
    exit 0
}

$claude = $null
try { $claude = Get-Command claude -ErrorAction Stop } catch { }
if (-not $claude) {
    Write-Host 'claude not found on PATH - scaffold is complete, start it yourself.' -ForegroundColor Yellow
    exit 0
}

Write-Host 'Starting Claude...' -ForegroundColor Cyan
Write-Host ''
claude
