# Turn-boundary typecheck — NOT YET ENABLED.
#
# Deliberately dormant. Do NOT wire this up on principle — a hook that blocks the end
# of a turn is the pattern that has caused trouble before. The evidence trigger for
# turning it on is specific: repeatedly shipping type errors. Absent that, the cost
# (a wrong verdict blocking work) outweighs the benefit.
#
# To turn on, add to settings.json "hooks":
#   "Stop": [{ "hooks": [{ "type": "command",
#     "command": "powershell -NoProfile -ExecutionPolicy Bypass -File C:/Users/jtakh/.claude/hooks/stop-typecheck.ps1" }]}]
#
# Adapted from app-foundation's stop-typecheck.sh, with one required change: that
# version hardcodes `npm run typecheck`, which exists in exactly one of the five
# projects here. This discovers the script instead (VERIFY-GATE: discovered, never
# assumed).
#
# Stop rather than PostToolUse on purpose: per-edit typechecking flags intentionally
# incomplete mid-refactor states and burns context on noise. A turn-boundary check
# runs once a coherent batch has landed.
#
# Exit 2 is what makes it self-correcting rather than merely informational: it blocks
# the stop and feeds stderr back. Claude Code overrides a Stop hook after 8
# consecutive blocks, so a wrong verdict cannot trap the session indefinitely.

try {
    $raw = [Console]::In.ReadToEnd()

    # Loop guard. A parse failure yields $false, failing toward RUNNING the check
    # rather than toward skipping it silently.
    $active = $false
    try { if ($raw) { $active = ($raw | ConvertFrom-Json).stop_hook_active -eq $true } } catch { }
    if ($active) { exit 0 }

    $root = $env:CLAUDE_PROJECT_DIR
    if (-not $root) { $root = (Get-Location).Path }
    if (-not (Test-Path (Join-Path $root 'package.json'))) { exit 0 }  # not a JS project

    $pkg = Get-Content (Join-Path $root 'package.json') -Raw | ConvertFrom-Json
    $names = @()
    if ($pkg.scripts) { $names = $pkg.scripts.PSObject.Properties.Name }

    # Cheapest check that can catch a type error, in preference order.
    $script = @('typecheck','check','tsc','lint') | Where-Object { $names -contains $_ } | Select-Object -First 1
    if (-not $script) { exit 0 }   # nothing to run — say nothing

    Push-Location $root
    try {
        $out = & npm run $script
        $code = $LASTEXITCODE
    } finally { Pop-Location }

    if ($code -ne 0) {
        [Console]::Error.WriteLine(($out | Select-Object -Last 20) -join "`n")
        [Console]::Error.WriteLine("npm run $script failed - fix before ending the turn")
        exit 2
    }
}
catch {
    # Never trap the session over a bug in this hook, but never fail silently either.
    [Console]::Error.WriteLine("stop-typecheck hook: $($_.Exception.Message)")
    exit 0
}
exit 0
