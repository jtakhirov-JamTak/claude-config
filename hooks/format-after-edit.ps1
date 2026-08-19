# PostToolUse formatter — runs Prettier on a file I just edited.
#
# Advisory only: this ALWAYS exits 0. A formatter that can block the session is a
# formatter that can stop work over a cosmetic problem, so it never does.
#
# PowerShell rather than bash on purpose: a .sh hook in this repo would be checked
# out CRLF on a fresh clone (core.autocrlf=true) and die with "bad interpreter".
# Invoked the same way as statusline.ps1.
#
# It stays silent unless it has something real to say — but it never fails silently
# (see non-negotiable #9 in app-foundation: a script that swallows its own error is
# indistinguishable from one that worked).

$FORMATTABLE = @('.ts','.tsx','.js','.jsx','.mjs','.cjs','.json','.css','.scss',
                 '.md','.mdx','.html','.yml','.yaml')

try {
    $raw = [Console]::In.ReadToEnd()
    if ([string]::IsNullOrWhiteSpace($raw)) { exit 0 }

    $path = ($raw | ConvertFrom-Json).tool_input.file_path
    if (-not $path) { exit 0 }
    # -ErrorAction: Test-Path *throws* on illegal path characters rather than
    # returning false, which leaked a stack trace for a case that should be a no-op.
    if (-not (Test-Path -LiteralPath $path -ErrorAction SilentlyContinue)) { exit 0 }

    $ext = [IO.Path]::GetExtension($path).ToLower()
    if ($FORMATTABLE -notcontains $ext) { exit 0 }

    # Walk up to the nearest package.json — the project root.
    $dir = Split-Path -Parent (Resolve-Path -LiteralPath $path).Path
    $root = $null
    while ($dir) {
        if (Test-Path (Join-Path $dir 'package.json')) { $root = $dir; break }
        $parent = Split-Path -Parent $dir
        if ($parent -eq $dir) { break }
        $dir = $parent
    }
    if (-not $root) { exit 0 }   # not a JS project — stay out of the way

    # Only format where the project has actually adopted Prettier. Reformatting a
    # project that never chose it would put noise in every diff the user reads.
    $uses = [bool](Get-ChildItem -LiteralPath $root -Force -File -ErrorAction SilentlyContinue |
                   Where-Object { $_.Name -like '.prettierrc*' -or $_.Name -like 'prettier.config.*' })
    if (-not $uses) {
        $pkg = Get-Content (Join-Path $root 'package.json') -Raw | ConvertFrom-Json
        $uses = ($null -ne $pkg.prettier) -or
                ($null -ne $pkg.devDependencies -and $null -ne $pkg.devDependencies.prettier)
    }
    if (-not $uses) { exit 0 }

    # Invoke the local binary directly rather than through npx. npx adds a resolution
    # step that can fail even when the binary is right there, and PowerShell's call
    # operator launches a .cmd shim happily -- the thing Node's spawnSync cannot do
    # (see the .cmd-shim rule in CLAUDE.md).
    $bin = Join-Path $root 'node_modules\.bin\prettier.cmd'
    if (-not (Test-Path -LiteralPath $bin)) {
        $bin = Join-Path $root 'node_modules\.bin\prettier'
        # Deps simply not installed yet. Expected state, not a failure -- stay quiet.
        if (-not (Test-Path -LiteralPath $bin)) { exit 0 }
    }

    Push-Location $root
    try {
        $out = & $bin --write --ignore-unknown $path
        if ($LASTEXITCODE -ne 0) {
            [Console]::Error.WriteLine("format hook: prettier exited $LASTEXITCODE on $path")
            if ($out) { [Console]::Error.WriteLine(($out | Select-Object -Last 5) -join "`n") }
        }
    } finally { Pop-Location }
}
catch {
    [Console]::Error.WriteLine("format hook: $($_.Exception.Message)")
}

exit 0
