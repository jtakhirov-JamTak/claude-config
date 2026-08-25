#!/usr/bin/env python3
"""PreToolUse hook for Bash AND PowerShell.

Two enforcement modes:
1. UNIVERSAL DENYLIST (all agents): destructive/bypass commands.
2. EVALUATOR ALLOWLIST: when the hook fires inside the `evaluator` subagent
   (agent_type in hook input), the shell is restricted to read-only inspection
   and test commands. Fail CLOSED for the evaluator.

Git handling is PARSE -> NORMALIZE -> MATCH, not line-oriented regex, because
the thing being protected against is a command CLASS, not a spelling. Adding
`-C repo` to a destructive command does not make it a different command; a rule
that only knows the bare spelling is bypassed by the global-option one. So every
git segment is tokenized, its leading NAME=VALUE environment assignments and git
global options (-C, -c, --git-dir, --work-tree, --config-env, ...) are lifted
off, and the rules match the resulting `git <subcommand> ...` form. The lifted
globals and env are then judged separately, because some of them (anything
setting core.hooksPath) ARE the bypass rather than a detail of it.

Regex over the raw line also produced FALSE positives: the old reset rule fired
on the path TEXT in `--git-dir=/tmp/r/dotgit` while missing the same command
with `--git-dir=/srv/repo`. Parsing removes both directions of that error, since
path text is no longer read as if it were the command.

Shell awareness: `tool_name` selects the parser. Bash and PowerShell differ in
three ways that matter here:
  * separators: bash has `;` `|` `&&` `||`; PowerShell 5.1 has `;` and `|` only
    (`&&`/`||` are PS7+, so they are split on but never assumed present).
  * file verbs: `cat`/`cp`/`rm` vs `Get-Content`/`Copy-Item`/`Remove-Item`.
  * aliases: `cat`, `gc`, `type` are all `Get-Content`. Commands are
    canonicalized to the cmdlet name BEFORE matching, so an alias cannot slip
    past a rule.
Git CLI syntax is identical in both shells, so the git rules are shared.

Field caveat: agent identity arrives as `agent_type`, the documented field for
hooks firing inside a subagent. `agent_name` is also read because it has been
seen in some payloads. If neither is present, evaluator mode cannot engage, and
there is NO LONGER a backstop for that: `isolation: worktree` was removed from
the evaluator so it can see uncommitted work, so this hook and the agent-scoped
Read hook are the containment.

Payload vs operand: a command string carries two kinds of text. OPERANDS are
part of the command — the verb, its flags, and the paths it opens, including a
redirect target. PAYLOAD is data the command merely transports: a heredoc body,
a PowerShell here-string, a quoted message. Payload is never executed and never
names a file being opened, so matching command rules against it produces pure
false positives — an apostrophe in prose read as an unterminated quote, a
filename mentioned in a commit message read as a file being opened.

So payload is removed before parsing, and only the operands are judged. The
distinction is kept sharp on purpose: `cat <<EOF > .env` is still blocked,
because the redirect target is an operand, and only the body between the
delimiters is dropped.
"""
import json
import re
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
# A NEWLINE separates commands in both shells. Leaving it out meant every
# token-based check — recursive delete, every git rule — saw only the first line
# of a multi-line command, so `npm test\nrm -rf ./src` was allowed. The regex
# file rules were unaffected (their `[^;|&]*` crosses newlines), which is why the
# gap survived: the .env cases still went red, so nothing looked broken.
SEPARATORS = ("&&", "||", "|", ";", "\n")
# A destructive command inside a substitution still runs.
SUBST = re.compile(r"\$\(([^()]*)\)|`([^`]*)`")

MIGRATION_DIR = r"(supabase/|prisma/|db/)?migrations/"
# EVERY `.env*` path is secret, with no exceptions to reason about. The
# non-secret example file is `env.example` — no leading dot — which does not
# contain the substring `.env` and so never matches this pattern in the first
# place. That is the whole point of the name: the guard needs no carve-out, so
# there is no carve-out to get out of step with write_guard.py or .gitignore.
ENVFILE = r"\.env"

ENV_ASSIGN = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", re.S)
PS_ENV_ASSIGN = re.compile(r"\$env:([A-Za-z_][A-Za-z0-9_]*)\s*=\s*['\"]?([^'\";|]*)", re.I)


def block(msg):
    print(msg, file=sys.stderr)
    sys.exit(2)


# --- Quote-aware lexing ------------------------------------------------------
# Purpose-built rather than shlex, because BOTH stock modes get a case wrong
# that this guard depends on:
#   * posix=False splits `--git-dir="C:\p with spaces\x"` into three tokens (it
#     only honours a quote that OPENS a token), which recreates the very bypass
#     this parser exists to close.
#   * posix=True strips the quotes, losing the quoted-ness needed to stop a
#     string literal such as `-m "the -n flag"` from faking a flag.
# Backslash is literal here: on Windows it is a path separator, not an escape.

def tokenize(cmd):
    """-> [(text, was_quoted), ...]. Raises ValueError on an unterminated quote."""
    toks, buf = [], []
    quoted = started = False
    inq = None
    for ch in cmd:
        if inq:
            if ch == inq:
                inq = None
            else:
                buf.append(ch)
            continue
        if ch in "'\"":
            inq, quoted, started = ch, True, True
            continue
        if ch.isspace():
            if started:
                toks.append(("".join(buf), quoted))
                buf, quoted, started = [], False, False
            continue
        buf.append(ch)
        started = True
    if inq:
        raise ValueError("unterminated quote")
    if started:
        toks.append(("".join(buf), quoted))
    return toks


def strip_comments(cmd):
    """Drop `#` comments that start outside a quoted string.

    Both shells treat `#` as a comment only at the start of a token, so `$#`
    and `a#b` are left alone. Without this, an apostrophe inside a comment —
    "the BOM'd file" — reads as an unterminated quote and the whole command is
    rejected. Blocking legitimate work is a defect, not caution. A commented-out
    command does not run, so nothing is lost by removing it before parsing.
    """
    out = []
    for line in cmd.split("\n"):
        inq, prev, cut = None, "", None
        for i, ch in enumerate(line):
            if inq:
                if ch == inq:
                    inq = None
            elif ch in "'\"":
                inq = ch
            elif ch == "#" and (i == 0 or prev.isspace()):
                cut = i
                break
            prev = ch
        out.append(line if cut is None else line[:cut])
    return "\n".join(out)


# --- Payload removal ---------------------------------------------------------
# `<<WORD`, `<<-WORD`, `<<'WORD'`. `<<<` is a here-string with no body and is
# deliberately not matched here.
HEREDOC_OP = re.compile(r"<<-?\s*(?:(['\"])([^'\"]+)\1|([A-Za-z_][A-Za-z0-9_]*))")
# PowerShell here-string opener: @' or @" as the last thing on the line.
PS_HERE_OPEN = re.compile(r"@(['\"])[ \t]*$")


def _heredoc_delims(line):
    """-> [(delimiter, start, end)] for heredocs OPENED on this line.

    Quote-aware: `echo "a << b"` opens nothing. Without that, a `<<` inside a
    string would swallow the rest of the command as if it were a body.
    """
    found, inq, i, n = [], None, 0, len(line)
    while i < n:
        ch = line[i]
        if inq:
            if ch == inq:
                inq = None
            i += 1
        elif ch in "'\"":
            inq = ch
            i += 1
        elif line.startswith("<<<", i):
            i += 3  # here-string: no body to skip
        elif line.startswith("<<", i):
            m = HEREDOC_OP.match(line, i)
            if not m:
                i += 2
                continue
            found.append((m.group(2) or m.group(3), m.start(), m.end()))
            i = m.end()
        else:
            i += 1
    return found


def strip_heredocs(cmd):
    """Drop heredoc BODIES, keep the operator line.

    The body is payload: never executed, and never a path the command opens. The
    line that introduces it is not — `cat <<EOF > .env` still names .env as a
    redirect target, so the `<<EOF` token is removed and everything else on that
    line survives to be judged.

    An unterminated heredoc swallows the remainder, which matches the shell: a
    body with no closing delimiter means the command never completes and nothing
    after it runs.
    """
    lines = cmd.split("\n")
    out, i = [], 0
    while i < len(lines):
        delims = _heredoc_delims(lines[i])
        if not delims:
            out.append(lines[i])
            i += 1
            continue
        kept, prev = [], 0
        for _d, start, end in delims:
            kept.append(lines[i][prev:start])
            prev = end
        kept.append(lines[i][prev:])
        out.append(" ".join(kept))
        i += 1
        for delim, _s, _e in delims:
            while i < len(lines) and lines[i].strip() != delim:
                i += 1
            i += 1  # drop the terminator line itself
    return "\n".join(out)


def strip_ps_herestrings(cmd):
    """PowerShell @'...'@ and @"..."@ bodies. Same rule as the bash heredoc.

    Whatever follows the closing delimiter on its line is kept, so
    `@'...'@ ; Remove-Item -Recurse x` is still judged.
    """
    lines = cmd.split("\n")
    out, i = [], 0
    while i < len(lines):
        m = PS_HERE_OPEN.search(lines[i])
        out.append(lines[i][:m.start()] if m else lines[i])
        i += 1
        if not m:
            continue
        close = m.group(1) + "@"
        while i < len(lines) and not lines[i].lstrip().startswith(close):
            i += 1
        if i < len(lines):
            tail = lines[i]
            out.append(tail[tail.find(close) + len(close):])
            i += 1
    return "\n".join(out)


def split_segments(cmd):
    """Split on shell separators that are OUTSIDE quotes.

    A plain regex split would cut `git commit -m "a|b"` in half and then fail to
    parse either piece.
    """
    out, buf = [], []
    inq = None
    i, n = 0, len(cmd)
    while i < n:
        ch = cmd[i]
        if inq:
            buf.append(ch)
            if ch == inq:
                inq = None
            i += 1
            continue
        if ch in "'\"":
            inq = ch
            buf.append(ch)
            i += 1
            continue
        hit = next((s for s in SEPARATORS if cmd.startswith(s, i)), None)
        if hit:
            out.append("".join(buf))
            buf = []
            i += len(hit)
            continue
        buf.append(ch)
        i += 1
    out.append("".join(buf))
    return [s for s in out if s.strip()]


def expand_substitutions(cmd):
    """Bodies of $(...) and backticks, recursively, as commands in their own right."""
    found, seen, work = [], set(), [cmd]
    while work:
        for m in SUBST.finditer(work.pop()):
            body = m.group(1) if m.group(1) is not None else m.group(2)
            if body and body.strip() and body not in seen:
                seen.add(body)
                found.append(body)
                work.append(body)
    return found


def strip_quoted(cmd):
    """Blank out quoted string bodies so flag and path matching cannot be fooled
    by a literal such as a commit message that names a flag."""
    return QUOTED.sub("''", cmd)


def canon_ps(seg):
    """Rewrite the first token of a segment to its canonical cmdlet name."""
    stripped = seg.lstrip()
    if not stripped:
        return seg
    pad = seg[: len(seg) - len(stripped)]
    parts = stripped.split(None, 1)
    head = parts[0].lower()
    rest = (" " + parts[1]) if len(parts) > 1 else ""
    return pad + PS_ALIASES.get(head, head) + rest


# --- Git parsing -------------------------------------------------------------
# Global options accepted BEFORE the subcommand. Value-taking ones consume the
# next token; the `--opt=value` spelling is handled generically.
GIT_GLOBAL_VALUE_OPTS = {
    "-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path",
    "--config-env", "--super-prefix", "--attr-source",
}
# Options that stand alone. Anything unknown is treated as standing alone too,
# and if that guess is wrong the subcommand check below fails CLOSED.
GIT_GLOBAL_FLAGS = {
    "-p", "-P", "--paginate", "--no-pager", "--bare", "--no-replace-objects",
    "--literal-pathspecs", "--glob-pathspecs", "--noglob-pathspecs",
    "--icase-pathspecs", "--no-optional-locks", "--no-lazy-fetch",
    "--no-advice", "--html-path", "--man-path", "--info-path", "--version",
    "-v", "--help", "-h",
}
# Options whose VALUE is free text. Blanking those values is what keeps a commit
# message that NAMES a destructive command from reading as one, while a quoted
# flag such as reset "--hard" still reads as the flag it is.
GIT_MSG_OPTS = {"-m", "--message", "-F", "--file"}
HOOKSPATH = re.compile(r"core\.hookspath", re.I)
SUBCOMMAND = re.compile(r"[A-Za-z][A-Za-z0-9._-]*$")


def parse_git(toks):
    """-> (env, globals, rest) for a git command, else None."""
    env, i = {}, 0
    while i < len(toks):
        m = ENV_ASSIGN.match(toks[i][0])
        if not m:
            break
        env[m.group(1).upper()] = m.group(2)
        i += 1
    if i >= len(toks) or toks[i][0].lower() not in ("git", "git.exe"):
        return None
    i += 1
    globs = []
    while i < len(toks):
        t = toks[i][0]
        if not t.startswith("-"):
            break
        if t.startswith("--") and "=" in t:
            globs.append(t)
            i += 1
        elif t in GIT_GLOBAL_VALUE_OPTS:
            globs.append(t + "=" + (toks[i + 1][0] if i + 1 < len(toks) else ""))
            i += 2
        else:
            globs.append(t)
            i += 1
    return env, globs, toks[i:]


def normalize_git(rest):
    """`git <subcommand> ...` with globals gone and free-text values blanked."""
    out, blank_next = [], False
    for text, _quoted in rest:
        if blank_next:
            out.append("''")
            blank_next = False
        elif text in GIT_MSG_OPTS:
            out.append(text)
            blank_next = True
        elif (text.startswith("--") and "=" in text
              and text.split("=", 1)[0] in GIT_MSG_OPTS):
            out.append(text.split("=", 1)[0] + "=''")
        else:
            out.append(text)
    return "git " + " ".join(out)


def ambient_env(sources, powershell):
    """Environment set EARLIER on the same command line.

    `export GIT_CONFIG_KEY_0=core.hooksPath ; git commit` and the PowerShell
    `$env:` spelling both set the variable for the git command that follows, so
    they belong to that command even though they are a separate segment. Only
    within one tool call: neither shell's variables survive to the next one.
    """
    env = {}
    for src in sources:
        if powershell:
            for k, v in PS_ENV_ASSIGN.findall(src):
                env[k.upper()] = v
            continue
        for seg in split_segments(src):
            try:
                toks = tokenize(seg)
            except ValueError:
                continue
            if not toks:
                continue
            start = 1 if toks[0][0].lower() in ("export", "set", "env") else 0
            for t, _q in toks[start:]:
                m = ENV_ASSIGN.match(t)
                if not m:
                    break
                env[m.group(1).upper()] = m.group(2)
    return env


def check_git(toks, extra_env=None):
    parsed = parse_git(toks)
    if parsed is None:
        return
    env, globs, rest = parsed
    if extra_env:
        env = dict(extra_env, **env)

    # core.hooksPath by ANY spelling is the bypass itself, whatever the
    # subcommand: -c core.hooksPath=, --config-env=core.hooksPath=,
    # GIT_CONFIG_KEY_n=core.hooksPath.
    for g in globs:
        if HOOKSPATH.search(g):
            block("Blocked: setting core.hooksPath on the git command line "
                  "repoints the hooks that verify the work. .githooks/pre-commit "
                  "is a release control - fix the check instead.")
    for k, v in env.items():
        if HOOKSPATH.search(k) or HOOKSPATH.search(v):
            block("Blocked: setting core.hooksPath through the environment "
                  "repoints the hooks that verify the work. .githooks/pre-commit "
                  "is a release control - fix the check instead.")

    if not rest:
        return  # bare `git`, `git --version` - nothing to police

    sub = rest[0][0].lower()
    if not SUBCOMMAND.match(sub):
        # An unknown global consumed the subcommand slot. Fail CLOSED and say so,
        # rather than matching rules against a string that is not a command.
        block(f"Blocked: could not identify the git subcommand (read {sub!r}). "
              f"The guard fails closed on git commands it cannot parse.")

    # GIT_CONFIG_* in front of a commit can rewrite config - including the hooks
    # path - for exactly that commit. Read-only subcommands keep it.
    if sub == "commit" and any(k.startswith("GIT_CONFIG") for k in env):
        block("Blocked: GIT_CONFIG_* in front of a commit can rewrite config "
              "(core.hooksPath included) for that commit. Commit without it.")

    # Case-sensitive, token-level: must run before the IGNORECASE rules below,
    # which cannot tell restore's -S from -s.
    check_git_restore(rest)

    normalized = normalize_git(rest)
    for pat, msg in GIT_RULES:
        if re.search(pat, normalized, re.IGNORECASE):
            block(f"Blocked: {msg}")


# --- Rules shared by both shells (git CLI syntax is identical) ---------------
# These match the NORMALIZED form, so each one covers every global-option
# spelling of its command class automatically.
GIT_RULES = [
    (r"git\s+commit\b[^;|&]*(--no-verify|\s-n\b)",
     "Bypassing commit verification is blocked. Fix the check instead."),
    # Only writes repoint the hooks. Reading the value is harmless, and
    # /new-app step 2 depends on it - over-blocking a read trains workarounds.
    (r"git\s+config\b[^;|&]*hooksPath\s+[^\s;|&]",
     "Repointing git hooks is blocked. .githooks/pre-commit is a release "
     "control. Reading the value with --get is fine."),
    (r"git\s+config\b[^;|&]*(--unset|--unset-all|--replace-all|--add)\b[^;|&]*hooksPath",
     "Removing or rewriting the git hooks path is blocked. .githooks/pre-commit "
     "is a release control."),
    # Every force form, not just the long one before an explicit main/master:
    # --force-with-lease and --force-if-includes rewrite history too, and a
    # leading-plus refspec is a force push spelled differently.
    (r"git\s+push\b[^;|&]*(--force\b|--force-with-lease|--force-if-includes|\s-f\b)",
     "Force-pushing is blocked. It rewrites published history - do it yourself "
     "if you mean it."),
    (r"git\s+push\b[^;|&]*\s\+[\w./-]+",
     "That refspec is a force push. Blocked - it rewrites published history."),
    (r"git\s+reset\s+--hard",
     "Discarding the working tree with reset --hard is blocked. Show the human "
     "what would be lost first."),
    (r"git\s+clean\s+-[a-zA-Z]*f",
     "Forced clean is blocked. Show the human what would be deleted first."),
    (r"git\s+checkout\s+(--\s|\.\s*$|\*)",
     "Discarding working-tree changes is blocked. Show the human first."),
    # `git restore` is NOT handled here - see check_git_restore(). A regex
    # cannot decide it, because these rules run with re.IGNORECASE and restore's
    # `-S` (staged, safe) is a different flag from `-s` (source, destructive).
]

# --- Bash-only file rules ----------------------------------------------------
# EVERY verb here is \b-anchored. Without that, the alternation matched inside
# ordinary English words — `ahead ` contains `head `, `committee ` contains
# `tee `, `unless ` contains `less `, `detail ` contains `tail ` — and since
# `[^;|&]*` crosses newlines, any such word anywhere earlier in the command
# reached forward to a filename mentioned later and blocked it. That is what
# actually fired on a commit message naming a dot-env file; the filename was
# never the trigger.
BASH_RULES = [
    # NOTE: recursive `rm` is handled by check_recursive_delete(), not here.
    # A prefix rule cannot see `rm -fr`, `rm -r -f`, or an `rm` that is not the
    # first command in the line.
    (r"(\bsed\s+-i|\bmv\s|\brm\s|>\s*|\btee\s)[^;|&]*" + MIGRATION_DIR,
     "Modifying migration files via shell is blocked. Create a new migration."),
    (r"\b(cat|echo|printf|tee)\b[^;|&]*(>>?|\|)\s*[^\s;|&]*" + ENVFILE + r"(\.|$|\s)",
     "Writing .env files via shell is blocked. Use the platform's secret manager."),
    # `tee` and `dd` name their output file as a DIRECT operand, with no
    # redirect for the rule above to key on: `tee .env` and `dd of=.env` both
    # write the file and both were allowed.
    (r"\b(tee|dd)\b[^;|&]*" + ENVFILE + r"(\.|$|\s|=)",
     "Writing .env files via shell is blocked. Use the platform's secret manager."),
    (r"\b(cat|less|more|head|tail|grep|cp|scp)\b\s+[^|;&]*" + ENVFILE + r"(\.|$|\s)",
     "Reading/copying .env files via shell is blocked."),
]

# --- PowerShell-only file rules (matched AFTER alias canonicalization) -------
PS_WRITE = (r"\b(set-content|add-content|out-file|new-item|remove-item|move-item|"
            r"copy-item|rename-item|clear-content)\b")
PS_READ = r"\b(get-content|select-string|copy-item|get-item)\b"

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
# The evaluator keeps `cat`, so the agent-scoped Read hook is not enough on its
# own - the same three paths have to be closed on the shell side too.
EVAL_FORBIDDEN_PATHS = ("progress.md", "session-context.md", "evals/")

EVAL_DENY_BASH = re.compile(
    r"(>>?|`|\$\(|\btee\b|\bsed\s+-i|\brm\b|\bmv\b|\bcp\b|\bchmod\b|\bchown\b|"
    r"\bln\b|\btouch\b|\bnpm\s+(i|install|ci|add)\b)")
EVAL_DENY_PS = re.compile(
    r"(>>?|\bset-content\b|\badd-content\b|\bout-file\b|\bnew-item\b|"
    r"\bremove-item\b|\bmove-item\b|\bcopy-item\b|\brename-item\b|"
    r"\bclear-content\b|\binvoke-expression\b|\bstart-process\b|"
    r"\bnpm\s+(i|install|ci|add)\b)")


def check_git_restore(rest):
    """Judge `git restore` on WHICH TREE it writes, not on the pathspec shape.

    `--staged` on its own rewrites the index only: the working copy is untouched,
    nothing uncommitted can be lost, and it is the exact twin of
    `git reset HEAD <path>`, which is allowed. Every other form overwrites the
    working copy - including the bare default, because restore with no tree flag
    IS `--worktree`.

    The rule this replaces keyed on the pathspec instead, as
    `(--staged\\s+|--worktree\\s+)*[.*]`, and got BOTH directions wrong. `[.*]` is
    a CHARACTER CLASS, so it fired on any path whose first character is a dot -
    `git restore --staged .gitignore` and `.claude/...` were blocked despite
    being pure unstaging. Meanwhile `git restore src/app.ts`, which silently
    discards uncommitted edits to that file, matched nothing and was allowed.

    Token-based rather than regex because GIT_RULES run with re.IGNORECASE, and
    restore's `-S` (staged) must not be confused with `-s` (source, which reads
    from another commit and overwrites the working copy).
    """
    if not rest or rest[0][0].lower() != "restore":
        return
    staged = worktree = False
    for text, _quoted in rest[1:]:
        if text == "--":
            break  # everything after `--` is a pathspec, not a flag
        if text.startswith("--"):
            name = text.split("=", 1)[0]
            if name == "--staged":
                staged = True
            elif name == "--worktree":
                worktree = True
        elif text.startswith("-") and len(text) > 1:
            # Short flags may be combined (-SW). Case matters: -S is staged,
            # -s is --source and is NOT a safety marker.
            if "S" in text[1:]:
                staged = True
            if "W" in text[1:]:
                worktree = True

    if worktree:
        block("Blocked: `git restore --worktree` overwrites the working copy and "
              "discards uncommitted changes. Show the human what would be lost "
              "first. To unstage only, use `git restore --staged <path>`.")
    if not staged:
        block("Blocked: `git restore` without --staged writes the WORKING TREE "
              "(that is the default), silently discarding uncommitted changes. "
              "Show the human what would be lost first. To unstage, use "
              "`git restore --staged <path>` or `git reset HEAD <path>` - both "
              "are allowed, including for dotted paths like .gitignore.")


def check_recursive_delete(toks, powershell):
    """Block recursive deletes wherever they appear in the line.

    `permissions.deny` matches on a command PREFIX, so a prefix rule sees only
    the exact flag spelling it names: not the reversed order, not the flags
    split apart, and not a delete that is the second command on the line. This
    reads the flags off the parsed tokens, so arrangement and position stop
    mattering.
    """
    if not toks:
        return
    head = toks[0][0].lower()

    if powershell:
        # canon_ps already resolved the aliases to remove-item. -Recurse is the
        # only -r* parameter Remove-Item takes, so any flag abbreviating to -r
        # means recursive.
        if head == "remove-item":
            for tok, _q in toks[1:]:
                if tok.lower().startswith("-r"):
                    block("Blocked: recursive delete. Show the human what "
                          "would be deleted first.")
        return

    if head != "rm":
        return
    for tok, _q in toks[1:]:
        if not tok.startswith("-"):
            continue
        if tok in ("--recursive", "-R"):
            block("Blocked: recursive delete. Show the human what would be "
                  "deleted first.")
        if tok.startswith("--"):
            continue
        # Combined short flags, in either order.
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
    low = cmd.replace("\\", "/").lower()
    for p in EVAL_FORBIDDEN_PATHS:
        if p in low:
            block("Evaluator context isolation: PROGRESS.md, session-context.md "
                  "and prior docs/evals/ are off-limits. Grade against "
                  "docs/SPEC.md and the running app only.")
    for segment in split_segments(cmd):
        seg = canon_ps(segment) if powershell else segment
        if not seg.strip():
            continue
        try:
            toks = tokenize(seg)
        except ValueError:
            block("Evaluator: command could not be parsed safely; blocked.")
        if not toks:
            continue
        head = toks[0][0].lower()
        if head not in allowed:
            block(f"Evaluator shell allowlist: '{head}' is not permitted. "
                  f"Allowed: {', '.join(sorted(allowed))} (git: status/diff "
                  f"only). Extend the list in shell_guard.py if a read-only "
                  f"tool is missing.")
        if head == "git":
            parsed = parse_git(toks)
            sub = parsed[2][0][0].lower() if parsed and parsed[2] else ""
            if sub not in EVAL_GIT_OK:
                block("Evaluator may only run status / diff. Git history and "
                      "mutations are off-limits (context isolation).")


def main():
    data = json.load(sys.stdin)
    tool = (data.get("tool_name") or "").lower()
    powershell = tool == "powershell"
    raw = (data.get("tool_input") or {}).get("command", "") or ""
    if not raw.strip():
        sys.exit(0)
    # Comments are not commands. Removing them first stops an apostrophe in
    # prose from being read as an unterminated quote.
    #
    # Comments BEFORE heredocs, deliberately: a `#` comment may itself contain
    # `<<`, and stripping heredocs first would read that as an opener and
    # swallow the real commands after it.
    raw = strip_comments(raw)
    # Payload is not command text. See the module docstring.
    raw = strip_ps_herestrings(raw) if powershell else strip_heredocs(raw)
    if not raw.strip():
        sys.exit(0)

    file_rules = PS_RULES if powershell else BASH_RULES
    flags = re.IGNORECASE if powershell else 0

    # A command hidden in a substitution still runs, so its body is inspected as
    # though it had been typed on a line of its own.
    sources = [raw] + expand_substitutions(raw)
    extra_env = ambient_env(sources, powershell)

    for source in sources:
        for segment in split_segments(source):
            seg = canon_ps(segment) if powershell else segment
            probe = strip_quoted(seg).replace("\\", "/")
            for pat, msg in file_rules:
                if re.search(pat, probe, flags):
                    block(f"Blocked: {msg}")
            try:
                toks = tokenize(seg)
            except ValueError:
                block("Blocked: unterminated quote - the guard cannot parse this "
                      "command, so it fails closed. Rewrite it and retry.")
            check_recursive_delete(toks, powershell)
            check_git(toks, extra_env)

    agent = (data.get("agent_type") or data.get("agent_name") or "").lower()
    if agent == "evaluator":
        check_evaluator(canon_ps(raw) if powershell else raw, powershell)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        print(f"shell_guard hook error (allowed): {e}", file=sys.stderr)
        sys.exit(0)
