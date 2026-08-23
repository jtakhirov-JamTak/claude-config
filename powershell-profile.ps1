# PowerShell 5.1 profile — VERSIONED COPY.
#
# This is the source of truth, tracked in the claude-config repo.
# The live file is $PROFILE, which on this machine sits under OneDrive.
#
# To install or update the live copy:   ~/.claude/sync-profile.ps1
# Never edit $PROFILE directly — edit this file and re-run sync-profile.ps1,
# or the next sync silently reverts your change.
#
# Paths are derived from $HOME rather than hardcoded, so this file works on any
# machine the OneDrive copy syncs to.

# Scaffold a new app from agentic-template-v4 and drop straight into Claude.
#
# The scaffold itself is defined once, in ~/.claude/new-app.ps1. This is only a
# shortcut to it — never copy the steps here.
#
#   new-app my-app-name              private repo, launches Claude in it
#   new-app my-app-name -NoLaunch    scaffold only, stay in the shell
#   new-app my-app-name -Public      public repo (irreversible once indexed)
#
# Invoked with & rather than `powershell -File` on purpose: Claude is an
# interactive TUI, and running it in the current session avoids nesting a shell
# around it. It also leaves you in the app folder when Claude exits.
# If execution policy ever blocks this, the policy-proof form is:
#   powershell -NoProfile -ExecutionPolicy Bypass -File $HOME\.claude\new-app.ps1 @args
function new-app { & (Join-Path $HOME '.claude\new-app.ps1') @args }
