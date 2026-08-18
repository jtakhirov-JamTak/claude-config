# Claude Code statusline — native PowerShell.
# Replaces statusline.sh: no bash, no jq.exe, no hardcoded winget path.
# Invoked as: powershell -NoProfile -ExecutionPolicy Bypass -File statusline.ps1
# Reads the session JSON payload on stdin, writes one ANSI-colored line to stdout.

$ErrorActionPreference = 'SilentlyContinue'

$e      = [char]27
$GREEN  = "$e[32m"
$YELLOW = "$e[33m"
$RED    = "$e[31m"
$CYAN   = "$e[36m"
$BLUE   = "$e[94m"
$PURPLE = "$e[35m"
$DIM    = "$e[90m"
$RESET  = "$e[0m"

$raw = [Console]::In.ReadToEnd()
try   { $j = $raw | ConvertFrom-Json }
catch { $j = $null }

$model = if ($j.model.display_name) { $j.model.display_name } else { 'Claude' }
$dir   = if ($j.workspace.current_dir) { $j.workspace.current_dir } else { '' }
$cost  = $j.cost.total_cost_usd

# Context window. Fall back to the model's own size rather than a hardcoded 200k,
# so the 1M-context variants don't report against the wrong denominator.
$maxTokens = $j.context_window.context_window_size
if (-not $maxTokens) {
    $maxTokens = if ($model -match '1m|\[1m\]') { 1000000 } else { 200000 }
}
$pct = $j.context_window.used_percentage
$pctInt = if ($null -ne $pct) { [int][math]::Floor([double]$pct) } else { 0 }
if ($pctInt -lt 0)   { $pctInt = 0 }
if ($pctInt -gt 100) { $pctInt = 100 }

$maxK     = [int]($maxTokens / 1000)
$currentK = [int]($maxK * $pctInt / 100)

$ctxColor = if ($pctInt -lt 50) { $GREEN } elseif ($pctInt -lt 75) { $YELLOW } else { $RED }

$filled = [int][math]::Floor($pctInt / 10)
if ($filled -gt 10) { $filled = 10 }
$bar = ('=' * $filled) + (' ' * (10 - $filled))

# Git branch, cached for 10s so we don't shell out on every render.
$branch = ''
if ($dir -and (Test-Path $dir)) {
    $cacheKey  = [math]::Abs($dir.GetHashCode())
    $cacheFile = Join-Path $env:TEMP "claude_git_branch_$cacheKey.txt"
    $fresh = $false
    if (Test-Path $cacheFile) {
        if (((Get-Date) - (Get-Item $cacheFile).LastWriteTime).TotalSeconds -lt 10) { $fresh = $true }
    }
    if ($fresh) {
        $branch = (Get-Content $cacheFile -Raw).Trim()
    } else {
        $branch = (& git -C $dir branch --show-current 2>$null | Select-Object -First 1)
        if ($null -eq $branch) { $branch = '' }
        Set-Content -Path $cacheFile -Value $branch -Encoding utf8 -NoNewline
    }
}

# Split on BOTH separators — the bash version only split on '/', so Windows
# paths passed through whole and then broke printf on the '\U' in '\Users'.
$folder = if ($dir) { ($dir -split '[\\/]' | Where-Object { $_ } | Select-Object -Last 1) } else { '' }

$out = "$PURPLE$model$RESET [$ctxColor$bar$RESET] $ctxColor$pctInt%$RESET | $BLUE${currentK}k/${maxK}k$RESET"
if ($cost -and [double]$cost -gt 0) { $out += " | $DIM`$$('{0:N2}' -f [double]$cost)$RESET" }
if ($branch) { $out += " | $CYAN$branch$RESET" }
if ($folder) { $out += " | $DIM$folder$RESET" }

[Console]::Out.Write($out)
