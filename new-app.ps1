# Canonical scaffold for a new app from agentic-template-v4.
#
# This file is the ONE definition of the scaffold. ~/.claude/commands/new-app.md
# delegates here rather than restating the steps, so there is nothing to keep in
# sync.
#
# Run it in your own terminal, then launch `claude` INSIDE the new folder.
# A session binds its project root at launch: project CLAUDE.md,
# .claude/settings.json and its hooks all resolve against that root.
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

    [string]$Root = (Join-Path $HOME 'dev'),

    [switch]$Public,

    # Scaffold only: leave you in the new folder without starting Claude.
    [switch]$NoLaunch
)

$ErrorActionPreference = 'Stop'
$TEMPLATE = 'jtakhirov-JamTak/agentic-template-v4'

# Stages are recorded as they complete so a failure can say how far it got. The thing
# you actually need to know on a failure is whether a GitHub repo now exists.
$script:Completed = @()
function Ok($msg) { $script:Completed += $msg }

function Fail($msg) {
    Write-Host ''
    Write-Host "FAILED: $msg" -ForegroundColor Red
    if ($script:Completed.Count -eq 0) {
        Write-Host '  Completed: nothing. Failed in preflight - no repo was created.' -ForegroundColor Yellow
    } else {
        Write-Host '  Completed:' -ForegroundColor Yellow
        foreach ($s in $script:Completed) { Write-Host "    - $s" }
        Write-Host '  Nothing after that ran.' -ForegroundColor Yellow
    }
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
if ((Resolve-Path $Root).Path.TrimEnd('\') -eq $HOME.TrimEnd('\')) {
    Fail 'Refusing to scaffold into the home directory. Use a dev root.'
}

try { Get-Command gh -ErrorAction Stop | Out-Null } catch { Fail 'gh CLI not found on PATH.' }
try { Get-Command git -ErrorAction Stop | Out-Null } catch { Fail 'git not found on PATH.' }

# PS 5.1 wraps a native command's stderr in ErrorRecords when it is redirected,
# and $ErrorActionPreference='Stop' makes that a TERMINATING error. `gh repo view`
# writes to stderr on the good path (repo does not exist), so a plain `2>$null`
# here killed the script exactly when the name was free. Drop EAP to Continue for
# the call and read the exit code, which is the only reliable signal.
$prevEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
gh repo view "jtakhirov-JamTak/$Name" 2>&1 | Out-Null
$repoExists = ($LASTEXITCODE -eq 0)
$ErrorActionPreference = $prevEap
if ($repoExists) { Fail "A GitHub repo named '$Name' already exists." }

Write-Host "  name '$Name' is free locally and on GitHub"

# The template has to be reachable before we try to create anything from it. Same EAP
# dance as above and for the same reason: `gh repo view` writes to stderr on paths that
# are not failures, and a plain `2>$null` under EAP=Stop killed this script once already.
$prevEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
gh repo view $TEMPLATE 2>&1 | Out-Null
$templateOk = ($LASTEXITCODE -eq 0)
$ErrorActionPreference = $prevEap
if (-not $templateOk) {
    Fail "Template '$TEMPLATE' is not reachable. Check the name and that gh is authenticated."
}
Write-Host "  template $TEMPLATE is reachable"

# The interpreter the hooks invoke, checked BEFORE anything is created. Hooks fail OPEN
# on their own errors by design, so a missing interpreter means the guardrails are
# silently decorative rather than loudly broken. Detection belongs here; the settings
# patch that acts on it stays in Step 4, because it edits a file that does not exist
# until after the clone.
$script:HasPython = $null -ne (Get-Command python -ErrorAction SilentlyContinue)
$script:HasPy     = $null -ne (Get-Command py     -ErrorAction SilentlyContinue)
if (-not $script:HasPython -and -not $script:HasPy) {
    Fail 'Neither `python` nor `py` resolves. The hooks would fail open and the guardrails would be decorative. Install Python, then re-run.'
}
if ($script:HasPython) {
    Write-Host '  interpreter: python'
} else {
    Write-Host '  interpreter: py (settings.json will be patched in Step 4)'
}

Ok 'Step 0 preflight - name free, dev root, gh/git, template reachable, interpreter resolves'

# --- Step 1: create from the template ---------------------------------------
Step 1 'Creating repo from template'

Set-Location $Root
$visibility = if ($Public) { '--public' } else { '--private' }
if ($Public) { Write-Host '  WARNING: creating PUBLIC. Public is effectively irreversible once indexed.' -ForegroundColor Yellow }

gh repo create $Name --template $TEMPLATE $visibility --clone
if (-not $?) { Fail 'gh repo create failed.' }
if (-not (Test-Path $target)) { Fail 'Clone did not produce the expected directory.' }

Set-Location $target
Ok "Step 1 GitHub repo created from template and cloned to $target  <-- THIS EXISTS NOW"

# --- Step 2: point git at the template's hooks ------------------------------
Step 2 'Wiring .githooks'

git config core.hooksPath .githooks
if (-not $?) { Fail 'git config core.hooksPath failed.' }

$hp = git config --get core.hooksPath
if ($hp -ne '.githooks') { Fail "core.hooksPath reads back as '$hp', expected '.githooks'." }
Write-Host "  core.hooksPath = $hp"
Ok 'Step 2 core.hooksPath wired to .githooks'

# --- Step 3: check pre-commit is executable ---------------------------------
Step 3 'Verifying pre-commit is executable'

# The template commits the hook 100755, so there is nothing to repair here - only
# something to catch. `git ls-files -s` reads THIS clone's index, which is where a
# checkout that lost the bit would show up, and CI/WSL/macOS silently skip a
# non-executable hook. Repairing it here instead would hide that regression.
$mode = (git ls-files -s .githooks/pre-commit) -split '\s+' | Select-Object -First 1
if ($mode -ne '100755') { Fail "pre-commit mode is $mode, expected 100755." }
Write-Host "  pre-commit mode = $mode"
Ok 'Step 3 pre-commit verified at mode 100755'

# --- Step 4: the interpreter the hooks call ---------------------------------
Step 4 'Pointing settings.json at the interpreter that exists'

# WHICH interpreter exists was settled in Step 0 preflight, before anything was created.
# This step only acts on that answer, because the file it patches does not exist until
# the clone above.
if ($script:HasPython) {
    Write-Host "  $(python --version 2>&1)"
} else {
    Write-Host '  `python` missing but `py` resolves — patching .claude/settings.json' -ForegroundColor Yellow
    $settings = '.claude/settings.json'
    $raw = Get-Content $settings -Raw
    $patched = $raw -replace '"command":\s*"python"', '"command": "py"'

    # PS 5.1's `-Encoding utf8` writes a BOM, and a BOM in settings.json is a
    # parser hazard. Write through .NET with BOM-less UTF-8 instead. .NET
    # resolves relative paths against the PROCESS directory rather than $PWD,
    # so the full path here is required, not decorative.
    $settingsFull = (Resolve-Path $settings).Path
    [System.IO.File]::WriteAllText($settingsFull, $patched,
        (New-Object System.Text.UTF8Encoding($false)))

    try { Get-Content $settings -Raw | ConvertFrom-Json | Out-Null } catch { Fail 'Patching settings.json produced invalid JSON. Restore it and fix by hand.' }
    # ConvertFrom-Json tolerates a BOM, so parsing cleanly does NOT prove the
    # encoding is right. Check the bytes.
    $bytes = [System.IO.File]::ReadAllBytes($settingsFull)
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        Fail 'settings.json was written with a UTF-8 BOM. It must be BOM-less.'
    }
    $left = (Select-String -Path $settings -Pattern '"command": "python"' -AllMatches).Count
    if ($left -ne 0) { Fail "settings.json still has $left python entries." }
    Write-Host "  patched, JSON valid, no BOM ($(py --version 2>&1)) - staged, not committed"
    git add $settings
}
Ok 'Step 4 interpreter verified and settings.json consistent with it'

# --- Done --------------------------------------------------------------------
# Everything below prints BEFORE Claude starts, because once it does it owns the
# terminal and anything written here scrolls away unread.
Write-Host ''
Write-Host '--- Scaffold ready ---------------------------------------------' -ForegroundColor Green
Write-Host "  $target"
Write-Host ''
Write-Host '  Verified: core.hooksPath, pre-commit mode 100755, interpreter resolves.'
Write-Host '  NOT verified (needs a live session): hook registration, permission rules.'
Write-Host '  STAGED, NOT COMMITTED: settings.json, if it was patched. Nothing else -'
Write-Host '  the mode bit is verified, not written. Review with `git status` and'
Write-Host '  commit it yourself.'
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
