#!/usr/bin/env python3
"""PreToolUse hook for Bash AND PowerShell.

Two enforcement modes:
1. UNIVERSAL DENYLIST (all agents): destructive/bypass commands.
2. EVALUATOR ALLOWLIST: when the hook fires inside the `evaluator` subagent
   (agent_type/agent_name in hook input), the shell is restricted to read-only
   inspection and test commands. Fail CLOSED for the evaluator.

Shell awareness: `tool_name` selects the parser. Bash and PowerShell differ in
three ways that matter here:
  * separators: bash has `;` `|` `&&` `||`; PowerShell 5.1 has `;` and `|` only
    (`&&`/`||` are PS7+, so they are split on but never assumed present).
  * file verbs: `cat`/`cp`/`rm` vs `Get-Content`/`Copy-Item`/`Remove-Item`.
  * aliases: `cat`, `gc`, `type` are all `Get-Content`. Commands are
    canonicalized to the cmdlet name BEFORE matching, so an alias cannot slip
    past a rule.
Git CLI syntax is identical in both shells, so the git rules are shared.

Field caveat: agent identity arrives as `agent_type` (documented for hooks
inside subagents) or `agent_name` (seen in some payloads). Both are checked.
If neither is present, evaluator mode cannot engage - the evaluator's
`isolation: worktree` checkout is the backstop. Verify field names on your
Claude Code version before trusting allowlist mode.
"""
import json
import re
import shlex
import sys

# --- PowerShell alias -> canonical cmdlet (lowercased) -----------------------
PS_ALIASES = {
    "gc": "get-content", "cat": "get-content", "type": "get-content",
    "sc": "set-content", "ac": "add-content",
    "ri": "remove-item", "rm": "remove-item", "del": "remove-item",
    "erase": "remove-item", "rd": "remove-item", "rmdir": "remove-item",
    "cpi": "copy-item", "cp": "copy-item", "copy": "copy-item",
    "mi": "move-item", "mv": "move-item", "move": "move-item",
    "ni": "new-item", "ren": "rename-item", "rni": "rename-item",
    "gci": "get-childitem", "ls": "get-childitem", "dir": "get-childitem",
    "sls": "select-string", "gcm": "get-command",
    "select": "select-object", "sort": "sort-object",
    "where": "where-object", "foreach": "foreach-object",
    "measure": "measure-object", "echo": "write-output",
    "write": "write-output", "iex": "invoke-expression",
    "sleep": "start-sleep", "gl": "get-location", "pwd": "get-location",
}

QUOTED = re.compile(r"'[^']*'|\"[^\"]*\"")
SEPARATORS = re.compile(r"\||;|&&|\|\|")
SEP_CAPTURE = re.compile(r"(\|\||&&|\||;)")

MIGRATION_DIR = r"(supabase/|prisma/|db/)?migrations/"
# .env.example / .env.sample / .env.template are committed on purpose
# (see .gitignore) and must stay readable; every other .env* is secret.
ENVFILE = r"\.env(?!\.example|\.sample|\.template)"


def strip_quoted(cmd):
    """Blank out quoted string bodies so flag and path matching cannot be fooled
    by a literal such as:  git commit -m "add -n handling"  ."""
    return QUOTED.sub("''", cmd)


def split_segments(cmd):
    """PS 5.1 has no &&/||, but splitting on them is harmless and covers PS7."""
    return [s for s in SEPARATORS.split(cmd) if s.strip()]


def canon_ps(cmd):
    """Rewrite the first token of every pipeline segment to its cmdlet name."""
    out = []
    for seg in SEP_CAPTURE.split(cmd):
        if seg in ("|", ";", "&&", "||"):
            out.append(seg)
            continue
        stripped = seg.lstrip()
        if not stripped:
            out.append(seg)
            continue
        pad = seg[: len(seg) - len(stripped)]
        parts = stripped.split(None, 1)
        head = parts[0].lower()
        rest = (" " + parts[1]) if len(parts) > 1 else ""
        out.append(pad + PS_ALIASES.get(head, head) + rest)
    return "".join(out)


# --- Rules shared by both shells (git CLI syntax is identical) ---------------
GIT_RULES = [
    (r"git\s+commit\b[^;|&]*(--no-verify|\s-n\b)",
     "Bypassing commit verification is blocked. Fix the check instead."),
    # Only writes repoint the hooks. Reading the value is harmless, and
    # /new-app step 2 depends on it — over-blocking a read trains workarounds.
    (r"git\s+config\b[^;|&]*hooksPath\s+[^\s;|&]",
     "Repointing git hooks is blocked. .githooks/pre-commit is a release "
     "control. Reading it (`git config --get core.hooksPath`) is fine."),
    (r"git\s+config\b[^;|&]*(--unset|--unset-all|--replace-all|--add)\b[^;|&]*hooksPath",
     "Removing or rewriting the git hooks path is blocked. .githooks/pre-commit "
     "is a release control."),
    # Every force form, not just `--force` before an explicit main/master:
    # --force-with-lease and --force-if-includes rewrite history too, and
    # `git push origin +main` is a force push spelled as a refspec.
    (r"git\s+push\b[^;|&]*(--force\b|--force-with-lease|--force-if-includes|\s-f\b)",
     "Force-pushing is blocked. It rewrites published history — do it yourself "
     "if you mean it."),
    (r"git\s+push\b[^;|&]*\s\+[\w./-]+",
     "That `+ref` refspec is a force push. Blocked — it rewrites published "
     "history."),
    (r"git\s+reset\s+--hard",
     "git reset --hard is blocked. Show the human what would be discarded first."),
    (r"git\s+clean\s+-[a-zA-Z]*f",
     "git clean -f is blocked. Show the human what would be deleted first."),
    (r"git\s+(checkout|restore)\s+(--\s|\.\s*$|\*)",
     "Discarding working-tree changes is blocked. Show the human first."),
    (r"git\s+restore\s+(--staged\s+|--worktree\s+)*[.*]",
     "git restore over the tree is blocked. Show the human what would be lost first."),
]

# --- Bash-only file rules ----------------------------------------------------
BASH_RULES = [
    # NOTE: recursive `rm` is handled by check_recursive_delete(), not here.
    # A prefix rule cannot see `rm -fr`, `rm -r -f`, or an `rm` that is not the
    # first command in the line.
    (r"(sed\s+-i|mv\s|rm\s|>\s*|tee\s)[^;|&]*" + MIGRATION_DIR,
     "Modifying migration files via shell is blocked. Create a new migration."),
    (r"(cat|echo|printf|tee)[^;|&]*(>>?|\|)\s*[^\s;|&]*" + ENVFILE + r"(\.|$|\s)",
     "Writing .env files via shell is blocked. Use the platform's secret manager."),
    (r"(cat|less|more|head|tail|grep|cp|scp)\s+[^|;&]*" + ENVFILE + r"(\.|$|\s)",
     "Reading/copying .env files via shell is blocked."),
]

# --- PowerShell-only file rules (matched AFTER alias canonicalization) -------
PS_WRITE = (r"(set-content|add-content|out-file|new-item|remove-item|move-item|"
            r"copy-item|rename-item|clear-content)")
PS_READ = r"(get-content|select-string|copy-item|get-item)"

PS_RULES = [
    # NOTE: Remove-Item is handled by check_recursive_delete(), which sees it
    # after alias canonicalization and does not depend on flag order.
    (PS_WRITE + r"[^;|]*" + MIGRATION_DIR,
     "Modifying migration files via shell is blocked. Create a new migration."),
    (r">>?\s*[^;|]*" + MIGRATION_DIR,
     "Modifying migration files via shell is blocked. Create a new migration."),
    (PS_WRITE + r"[^;|]*" + ENVFILE + r"(\.|\s|$)",
     "Writing .env files via shell is blocked. Use the platform's secret manager."),
    (r">>?\s*[^\s;|]*" + ENVFILE + r"(\.|\s|$)",
     "Writing .env files via shell is blocked. Use the platform's secret manager."),
    (PS_READ + r"[^;|]*" + ENVFILE + r"(\.|\s|$)",
     "Reading/copying .env files via shell is blocked."),
]

# --- Evaluator allowlists ----------------------------------------------------
EVAL_ALLOWED_BASH = {"npm", "npx", "node", "curl", "jq", "cat", "ls", "grep",
                     "head", "tail", "find", "wc", "diff", "pwd", "echo",
                     "which", "sleep", "git"}
EVAL_ALLOWED_PS = {"npm", "npx", "node", "curl", "jq", "git", "get-content",
                   "get-childitem", "select-string", "measure-object",
                   "write-output", "test-path", "resolve-path", "select-object",
                   "sort-object", "where-object", "foreach-object",
                   "start-sleep", "get-command", "compare-object",
                   "get-location", "split-path", "join-path"}
EVAL_GIT_OK = {"status", "diff"}  # git log is forbidden by the isolation protocol

EVAL_DENY_BASH = re.compile(
    r"(>>?|`|\$\(|\btee\b|\bsed\s+-i|\brm\b|\bmv\b|\bcp\b|\bchmod\b|\bchown\b|"
    r"\bln\b|\btouch\b|\bnpm\s+(i|install|ci|add)\b)")
EVAL_DENY_PS = re.compile(
    r"(>>?|\bset-content\b|\badd-content\b|\bout-file\b|\bnew-item\b|"
    r"\bremove-item\b|\bmove-item\b|\bcopy-item\b|\brename-item\b|"
    r"\bclear-content\b|\binvoke-expression\b|\bstart-process\b|"
    r"\bnpm\s+(i|install|ci|add)\b)")


def block(msg):
    print(msg, file=sys.stderr)
    sys.exit(2)


def check_recursive_delete(cmd, powershell):
    """Block recursive deletes wherever they appear in the line.

    `permissions.deny` matches on a command PREFIX, so `Bash(rm -rf:*)` sees
    `rm -rf x` and nothing else: not `rm -fr x`, not `rm -r -f x`, and not
    `cd s ; rm -rf x`, where `rm` is not the first token. This walks every
    segment and reads the flags, so arrangement and position stop mattering.
    """
    for segment in split_segments(cmd):
        toks = segment.split()
        if not toks:
            continue
        head = toks[0].lower()

        if powershell:
            # canon_ps already resolved rm/del/ri/rd/erase -> remove-item.
            # -Recurse is the only -r* parameter Remove-Item takes, so any flag
            # abbreviating to -r means recursive: -r, -rec, -Recurse:$true.
            if head == "remove-item":
                for tok in toks[1:]:
                    if tok.lower().startswith("-r"):
                        block("Blocked: recursive delete. Show the human what "
                              "would be deleted first.")
            continue

        if head != "rm":
            continue
        for tok in toks[1:]:
            if not tok.startswith("-"):
                continue
            if tok == "--recursive" or tok == "-R":
                block("Blocked: recursive delete. Show the human what would be "
                      "deleted first.")
            if tok.startswith("--"):
                continue
            # Combined short flags: -rf, -fr, -r, -Rf ...
            if "r" in tok[1:] or "R" in tok[1:]:
                block("Blocked: recursive delete. Show the human what would be "
                      "deleted first.")


def check_evaluator(cmd, powershell):
    deny = EVAL_DENY_PS if powershell else EVAL_DENY_BASH
    allowed = EVAL_ALLOWED_PS if powershell else EVAL_ALLOWED_BASH
    if deny.search(cmd):
        block("Evaluator is read-only: redirection, file mutation, and installs "
              "are blocked. Inspect and test only; report findings instead of "
              "fixing.")
    for segment in split_segments(cmd):
        seg = segment.strip()
        if not seg:
            continue
        if powershell:
            toks = seg.split()
        else:
            try:
                toks = shlex.split(seg)
            except ValueError:
                # Unbalanced quotes: fail CLOSED for the evaluator.
                block("Evaluator: command could not be parsed safely; blocked.")
        if not toks:
            continue
        head = toks[0].lower()
        if head not in allowed:
            block(f"Evaluator shell allowlist: '{head}' is not permitted. "
                  f"Allowed: {', '.join(sorted(allowed))} (git: status/diff "
                  f"only). Extend the list in scripts/hooks/shell_guard.py if a "
                  f"read-only tool is missing.")
        if head == "git" and (len(toks) < 2 or toks[1].lower() not in EVAL_GIT_OK):
            block("Evaluator may only run `git status` / `git diff`. Git history "
                  "and mutations are off-limits (context isolation).")


def main():
    data = json.load(sys.stdin)
    tool = (data.get("tool_name") or "").lower()
    powershell = tool == "powershell"
    raw = (data.get("tool_input") or {}).get("command", "") or ""
    if not raw.strip():
        sys.exit(0)

    # Normalize for matching: canonical cmdlet names, quote-stripped so string
    # literals cannot hide or fake a flag, and forward slashes so a Windows
    # path cannot dodge a rule written with `/`.
    norm = canon_ps(raw) if powershell else raw
    probe = strip_quoted(norm).replace("\\", "/")

    rules = GIT_RULES + (PS_RULES if powershell else BASH_RULES)
    flags = re.IGNORECASE if powershell else 0
    for pat, msg in rules:
        if re.search(pat, probe, flags):
            block(f"Blocked: {msg}")

    check_recursive_delete(probe, powershell)

    agent = (data.get("agent_type") or data.get("agent_name") or "").lower()
    if agent == "evaluator":
        check_evaluator(norm, powershell)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        print(f"shell_guard hook error (allowed): {e}", file=sys.stderr)
        sys.exit(0)
