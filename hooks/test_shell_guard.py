#!/usr/bin/env python3
"""Regression + mutation test for shell_guard.py.

Run:  python test_shell_guard.py
      python test_shell_guard.py --mutate

Each case names the exit code it must produce. BLOCK cases must exit 2; ALLOW
cases must exit 0. A rule that stops firing turns its BLOCK case red; a rule
that over-matches turns an ALLOW case red. Both directions are represented, so
a pass means something. Add a case here before changing any pattern.

--mutate is the check that the git-global normalization is what is actually
catching the global-option forms, rather than some incidental substring match.
It copies the guard, disables ONLY the global-option lifting, and asserts that
exactly the labels in MUTATION_EXPECT_RED turn red and nothing else moves. That
assertion fails in both directions: if the fix stops working the mutation stops
distinguishing anything, and if a rule starts over-matching, a case outside the
named set flips and the run fails.
"""
import json
import os
import subprocess
import sys
import tempfile

GUARD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shell_guard.py")

# The single line that performs git-global normalization, and the replacement
# that disables it while leaving quoted-value blanking intact. Narrow on
# purpose: a mutation that also broke the blanking would turn unrelated cases
# red and prove less.
MUTATION_ANCHOR = "    normalized = normalize_git(rest)"
MUTATION_PATCH = "    normalized = normalize_git(toks[1:])"

# (tool, command, agent, expect_exit, label)
CASES = [
    # ---- git rules, Bash ----
    ("Bash", "git commit --no-verify -m x", "", 2, "bash --no-verify"),
    ("Bash", "git commit -n -m x", "", 2, "bash -n shorthand"),
    ("Bash", "git config core.hooksPath /tmp/x", "", 2, "bash hooksPath write"),
    ("Bash", "git config --local core.hooksPath /tmp/x", "", 2, "hooksPath write with scope"),
    ("Bash", "git config --unset core.hooksPath", "", 2, "hooksPath unset"),
    ("Bash", "git config --replace-all core.hooksPath x", "", 2, "hooksPath replace-all"),
    # Reads must stay allowed: /new-app step 2 verifies the value this way, and
    # blocking a read teaches the agent to route around the guard.
    ("Bash", "git config core.hooksPath", "", 0, "hooksPath bare read allowed"),
    ("Bash", "git config --get core.hooksPath", "", 0, "hooksPath --get allowed"),
    ("Bash", "git config --get-all core.hooksPath", "", 0, "hooksPath --get-all allowed"),
    ("PowerShell", "git config --get core.hooksPath", "", 0, "ps hooksPath --get allowed"),
    ("PowerShell", "git config core.hooksPath .githooks", "", 2, "ps hooksPath write"),
    ("Bash", "git reset --hard HEAD~1", "", 2, "bash reset --hard"),
    ("Bash", "git clean -fd", "", 2, "bash clean -f"),
    ("Bash", "git checkout -- .", "", 2, "bash checkout --"),
    ("Bash", "git restore .", "", 2, "bash restore ."),
    # ---- git restore: judged on WHICH TREE it writes, not the pathspec shape --
    # The rule this replaces was `(--staged\s+|--worktree\s+)*[.*]`, a CHARACTER
    # CLASS, so it fired on any path starting with a dot while missing every
    # destructive restore of a normal path. Both directions are pinned here.
    #
    # ALLOW: --staged rewrites the index only. The working copy is untouched, so
    # nothing uncommitted can be lost. Twin of `git reset HEAD <path>`.
    ("Bash", "git restore --staged .gitignore", "", 0,
     "restore --staged dotfile allowed (was the over-block)"),
    ("Bash", "git restore --staged .claude/exceptions.md", "", 0,
     "restore --staged dotted dir allowed (was the over-block)"),
    ("PowerShell", "git restore --staged .gitignore", "", 0,
     "restore --staged dotfile allowed, ps"),
    ("Bash", "git restore --staged src/app.ts", "", 0,
     "restore --staged ordinary path allowed"),
    ("Bash", "git restore --staged .", "", 0,
     "restore --staged . unstages all, working tree untouched"),
    ("Bash", "git restore --staged *.ts", "", 0, "restore --staged glob allowed"),
    ("Bash", "git restore -S .gitignore", "", 0,
     "restore -S is the short --staged, allowed"),
    ("Bash", "git restore --staged -- .gitignore", "", 0,
     "restore --staged with -- separator allowed"),
    # BLOCK: anything that writes the working copy, including the bare default,
    # because restore with no tree flag IS --worktree.
    ("Bash", "git restore .gitignore", "", 2,
     "restore of a dotfile WITHOUT --staged still blocked"),
    ("Bash", "git restore src/app.ts", "", 2,
     "restore of one file discards its edits - was silently ALLOWED before"),
    ("Bash", "git restore --worktree .gitignore", "", 2,
     "explicit --worktree blocked even on a dotfile"),
    ("Bash", "git restore --staged --worktree .gitignore", "", 2,
     "--staged does not excuse an explicit --worktree"),
    ("Bash", "git restore -W src/app.ts", "", 2, "short -W blocked"),
    ("Bash", "git restore -SW src/app.ts", "", 2,
     "combined -SW still writes the worktree"),
    # Case matters: -s is --source (reads another commit INTO the working copy),
    # not -S. GIT_RULES run with re.IGNORECASE and cannot tell these apart, which
    # is why this check is token-based.
    ("Bash", "git restore -s HEAD~1 src/app.ts", "", 2,
     "-s is --source, NOT --staged: must still block"),
    ("Bash", "git restore -- .gitignore", "", 2,
     "-- separator without --staged still blocked"),
    ("Bash", "npm test && git restore .", "", 2, "restore after && still blocked"),
    ("PowerShell", "npm test ; git restore src/app.ts", "", 2,
     "restore after ; still blocked, ps"),
    ("Bash", "npm test && git reset --hard", "", 2, "bash chained reset"),
    # ---- git rules, PowerShell ----
    ("PowerShell", "git commit --no-verify -m x", "", 2, "ps --no-verify"),
    ("PowerShell", "git commit -n -m x", "", 2, "ps -n shorthand"),
    ("PowerShell", "git config core.hooksPath C:/tmp/x", "", 2, "ps hooksPath"),
    ("PowerShell", "git reset --hard HEAD~1", "", 2, "ps reset --hard"),
    ("PowerShell", "git clean -fd", "", 2, "ps clean -f"),
    ("PowerShell", "git restore .", "", 2, "ps restore ."),
    ("PowerShell", "npm test ; git reset --hard", "", 2, "ps chained reset"),

    # ==== A1: git GLOBAL OPTIONS =============================================
    # Adding a global option does not make it a different command. Each of
    # these exited 0 before the parse/normalize rewrite.
    ("Bash", "git -C repo reset --hard", "", 2, "gg -C reset"),
    ("PowerShell", "git -C repo reset --hard", "", 2, "gg -C reset ps"),
    ("Bash", "git -c color.ui=false reset --hard", "", 2, "gg -c reset"),
    ("Bash", "git --git-dir=/srv/repo reset --hard", "", 2, "gg --git-dir= reset"),
    ("Bash", "git --git-dir /srv/repo reset --hard", "", 2, "gg --git-dir space reset"),
    ("Bash", "git --work-tree=/tmp/r checkout -- .", "", 2, "gg --work-tree checkout"),
    ("Bash", "git -C repo clean -fd", "", 2, "gg -C clean"),
    ("Bash", "git -C repo push --force", "", 2, "gg -C push force"),
    ("Bash", "git -C repo push origin +main", "", 2, "gg -C push refspec"),
    ("Bash", "git -C repo commit --no-verify -m x", "", 2, "gg -C no-verify"),
    ("Bash", "git -C repo commit -n -m x", "", 2, "gg -C -n"),
    ("Bash", "git -C repo restore .", "", 2, "gg -C restore"),
    ("Bash", "git -p -C repo reset --hard", "", 2, "gg stacked globals reset"),
    # Quoted Windows paths containing spaces: whitespace splitting would parse
    # these wrong and recreate the bypass.
    ("Bash", 'git -C "C:\\path with spaces\\repo" reset --hard', "", 2, "gg spaced -C reset"),
    ("PowerShell", 'git -C "C:\\path with spaces\\repo" reset --hard', "", 2, "gg spaced -C reset ps"),
    ("Bash", 'git --git-dir="C:\\path with spaces\\repo\\.git" reset --hard', "", 2, "gg spaced --git-dir reset"),
    # Same command with no `.git` in the path. The one above is caught even by a
    # broken guard, because the literal text `.git reset --hard` happens to
    # contain the pattern — that coincidence WAS the old false positive. This
    # one has no such text, so only real parsing catches it.
    ("Bash", 'git --git-dir="C:\\path with spaces\\repo" reset --hard', "", 2, "gg spaced --git-dir reset no-dotgit"),
    ("Bash", 'git --work-tree="C:\\path with spaces\\repo" checkout -- .', "", 2, "gg spaced --work-tree checkout"),
    ("PowerShell", 'git --work-tree="C:\\path with spaces\\repo" checkout -- .', "", 2, "gg spaced --work-tree checkout ps"),
    # Chaining and substitution.
    ("Bash", "npm test && git -C repo reset --hard", "", 2, "gg chained reset"),
    ("PowerShell", "npm test ; git -C repo reset --hard", "", 2, "gg chained reset ps"),
    ("Bash", "echo $(git -C repo reset --hard)", "", 2, "gg substitution reset"),
    ("Bash", "echo `git -C repo reset --hard`", "", 2, "gg backtick reset"),

    # ==== A1: hooks-path / config injection ==================================
    # Blocked by the lifted-globals policy, NOT by normalization, so these stay
    # green under --mutate.
    ("Bash", "git -c core.hooksPath=/tmp/x commit -m y", "", 2, "hp -c commit"),
    ("PowerShell", "git -c core.hooksPath=C:/tmp/x commit -m y", "", 2, "hp -c commit ps"),
    ("Bash", "git -c core.hooksPath=/tmp/x status", "", 2, "hp -c any subcommand"),
    ("Bash", "git --config-env=core.hooksPath=EVIL commit -m y", "", 2, "hp --config-env"),
    ("Bash", "GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.hooksPath GIT_CONFIG_VALUE_0=/tmp/x git commit -m y",
     "", 2, "hp env inline"),
    ("Bash", "export GIT_CONFIG_KEY_0=core.hooksPath ; git commit -m y", "", 2, "hp env export"),
    ("PowerShell", "$env:GIT_CONFIG_KEY_0='core.hooksPath' ; git commit -m y", "", 2, "hp env ps"),
    ("Bash", "GIT_CONFIG_GLOBAL=/tmp/evil git commit -m y", "", 2, "hp GIT_CONFIG_GLOBAL commit"),
    # GIT_DIR / GIT_WORK_TREE only say WHERE. Destructive verbs are caught by
    # the normalized rules; read-only ones stay allowed (over-blocking is a
    # defect, per the handoff).
    ("Bash", "GIT_DIR=/srv/repo/.git git reset --hard", "", 2, "gg GIT_DIR reset"),
    ("Bash", "GIT_WORK_TREE=/srv/repo git checkout -- .", "", 2, "gg GIT_WORK_TREE checkout"),
    ("Bash", "GIT_DIR=/srv/repo/.git git status", "", 0, "GIT_DIR status allowed"),
    ("Bash", "GIT_WORK_TREE=/srv/repo git diff --stat", "", 0, "GIT_WORK_TREE diff allowed"),
    ("Bash", "GIT_CONFIG_GLOBAL=/tmp/x git status", "", 0, "GIT_CONFIG read-only allowed"),

    # ==== A1: global options must NOT over-block ==============================
    ("Bash", "git -C repo status", "", 0, "gg -C status allowed"),
    ("Bash", "git -c color.ui=false status", "", 0, "gg -c status allowed"),
    ("PowerShell", "git -c color.ui=false status", "", 0, "gg -c status allowed ps"),
    ("Bash", 'git -C "C:\\path with spaces\\repo" status', "", 0, "gg spaced -C status allowed"),
    ("Bash", 'git -C "C:\\path with spaces\\repo" diff --stat', "", 0, "gg spaced -C diff allowed"),
    ("PowerShell", 'git -C "C:\\path with spaces\\repo" status', "", 0, "gg spaced -C status allowed ps"),
    ("Bash", "git -C repo log --oneline", "", 0, "gg -C log allowed"),
    # ---- B4: `git reset` narrowed from a blanket block to the destructive form
    # The deny rule was Bash(git reset:*), which blocked unstaging — an
    # over-block. It is now Bash(git reset --hard:*). Both halves of the pair are
    # asserted here so neither direction can regress silently.
    ("Bash", "git reset HEAD file", "", 0, "B4 ALLOW: reset HEAD file (unstage)"),
    ("PowerShell", "git reset HEAD file", "", 0, "B4 ALLOW: reset HEAD file, ps"),
    ("Bash", "git reset HEAD src/app.ts", "", 0, "B4 ALLOW: unstage a path"),
    ("Bash", "git reset", "", 0, "B4 ALLOW: bare reset (unstage all)"),
    ("Bash", "git reset --soft HEAD~1", "", 0, "reset --soft allowed"),
    ("Bash", "git reset --mixed HEAD", "", 0, "B4 ALLOW: reset --mixed"),
    ("Bash", "git reset --hard", "", 2, "B4 BLOCK: reset --hard"),
    ("PowerShell", "git reset --hard", "", 2, "B4 BLOCK: reset --hard, ps"),
    ("Bash", "git reset --hard HEAD~3", "", 2, "B4 BLOCK: reset --hard with ref"),
    # The deny rule is a prefix matcher and cannot see any of these; the hook can.
    ("Bash", "git -C repo reset --hard", "", 2, "B4 BLOCK: --hard behind -C"),
    ("Bash", "npm test && git reset --hard", "", 2, "B4 BLOCK: --hard after &&"),
    ("Bash", "git status --porcelain", "", 0, "porcelain allowed"),
    ("Bash", "git --version", "", 0, "git --version allowed"),
    ("Bash", "git --no-pager diff", "", 0, "no-pager diff allowed"),

    # ==== A1: quoting must not be usable in either direction ==================
    # A quoted FLAG is still that flag.
    ("Bash", 'git reset "--hard"', "", 2, "quoted flag still a flag"),
    ("PowerShell", "git reset '--hard'", "", 2, "quoted flag still a flag ps"),
    # A message that NAMES a destructive command is just text.
    ("Bash", 'git commit -m "reset --hard is what I avoided"', "", 0, "message naming reset"),
    ("Bash", 'git commit -m "push --force considered harmful"', "", 0, "message naming force push"),
    ("Bash", 'git commit -m "a|b pipes in the message"', "", 0, "message containing a pipe"),
    # Unparseable input fails CLOSED rather than sliding past the rules.
    ("Bash", 'git -C "unterminated reset --hard', "", 2, "unterminated quote fails closed"),
    ("Bash", "git --unknownopt /srv/repo reset --hard", "", 2, "unknown global fails closed"),
    # ...but a comment is not unparseable input. An apostrophe in prose must not
    # take out an ordinary command — that over-block is a defect too.
    ("Bash", "echo hi  # writes the BOM'd file", "", 0, "apostrophe in bash comment"),
    ("PowerShell", "Write-Output hi  # don't block this", "", 0, "apostrophe in ps comment"),
    ("Bash", "git status  # it's fine", "", 0, "apostrophe in comment after git"),
    ("Bash", 'echo "a#b"', "", 0, "hash inside quotes is not a comment"),
    ("Bash", "echo $#", "", 0, "shell variable $# is not a comment"),
    ("Bash", "git commit -m x  # done", "", 0, "trailing comment on a commit"),
    # A comment must not RESCUE a real command, in either arrangement.
    ("Bash", "git reset --hard  # cleaning up", "", 2, "comment does not rescue reset"),
    ("Bash", "# git reset --hard", "", 0, "fully commented-out command does not run"),
    ("Bash", "npm test  # then git -C repo reset --hard", "", 0, "destructive text inside a comment"),

    # ---- .env, both shells ----
    ("Bash", "cat .env", "", 2, "bash read .env"),
    ("Bash", "echo K=1 >> .env", "", 2, "bash write .env"),
    ("PowerShell", "Get-Content .env", "", 2, "ps read .env"),
    ("PowerShell", "gc .env", "", 2, "ps read .env via alias gc"),
    ("PowerShell", "type .env", "", 2, "ps read .env via alias type"),
    ("PowerShell", "Set-Content .env 'K=1'", "", 2, "ps write .env"),
    ("PowerShell", "'K=1' > .env", "", 2, "ps redirect .env"),
    ("PowerShell", "Add-Content .env.local 'K=1'", "", 2, "ps append .env.local"),
    # ---- migrations, both shells ----
    ("Bash", "sed -i s/a/b/ supabase/migrations/001.sql", "", 2, "bash edit migration"),
    ("PowerShell", "Set-Content supabase/migrations/001.sql 'x'", "", 2, "ps edit migration"),
    ("PowerShell", "Set-Content supabase\\migrations\\001.sql 'x'", "", 2, "ps edit migration backslash"),
    ("PowerShell", "'x' >> db/migrations/002.sql", "", 2, "ps append migration"),
    # ---- recursive delete ----
    ("Bash", "rm -rf ~", "", 2, "bash rm -rf home"),
    ("PowerShell", "Remove-Item -Recurse -Force C:/foo", "", 2, "ps recursive delete"),
    ("PowerShell", "ri -Recurse foo", "", 2, "ps recursive delete via alias ri"),
    # ---- quote handling: a literal must not fake a flag ----
    ("Bash", 'git commit -m "document the -n flag"', "", 0, "bash -n inside quotes is not a flag"),
    ("PowerShell", 'git commit -m "document the -n flag"', "", 0, "ps -n inside quotes is not a flag"),
    # ---- ALLOW cases: ordinary work must not be blocked ----
    # ---- B3: the secret class is EVERY .env*, the example file is env.example ----
    # These four flipped from ALLOW to BLOCK when the .example/.sample/.template
    # carve-out was removed. `.env.example` is now secret-shaped like the rest,
    # and the non-secret name carries no leading dot.
    ("PowerShell", "Get-Content .env.example", "", 2, "ps .env.example now blocked (B3)"),
    ("Bash", "cat .env.sample", "", 2, "bash .env.sample now blocked (B3)"),
    ("Bash", "cat .env.template", "", 2, "bash .env.template now blocked (B3)"),
    ("PowerShell", "Get-Content .env.local", "", 2, "ps .env.local still blocked"),
    ("Bash", "cat .env.production", "", 2, "bash .env.production still blocked"),
    ("Bash", "cat .env", "", 2, "bash .env still blocked"),
    # env.example — no leading dot — is the supported non-secret example file.
    ("Bash", "cat env.example", "", 0, "bash read env.example allowed"),
    ("PowerShell", "Get-Content env.example", "", 0, "ps read env.example allowed"),
    ("Bash", "cp env.example .env", "", 2, "copying env.example ONTO .env still blocked"),
    ("Bash", "echo 'X=1' > env.example", "", 0, "bash write env.example allowed"),
    ("PowerShell", "Set-Content env.example 'X=1'", "", 0, "ps write env.example allowed"),
    ("Bash", "cat config/env.example", "", 0, "env.example in a subdir allowed"),
    ("Bash", "npm test", "", 0, "bash npm test"),
    ("Bash", "git status", "", 0, "bash git status"),
    ("Bash", "git commit -m 'feat: add thing'", "", 0, "bash ordinary commit"),
    ("Bash", "cat src/index.ts", "", 0, "bash read source"),
    ("PowerShell", "npm test", "", 0, "ps npm test"),
    ("PowerShell", "git status", "", 0, "ps git status"),
    ("PowerShell", "git commit -m 'feat: add thing'", "", 0, "ps ordinary commit"),
    ("PowerShell", "Get-Content src/index.ts", "", 0, "ps read source"),
    ("PowerShell", "Get-ChildItem .", "", 0, "ps list dir"),
    ("PowerShell", "Set-Content src/new.ts 'x'", "", 0, "ps write ordinary source"),
    ("PowerShell", "Write-Output 'hello'", "", 0, "ps echo"),
    # ---- recursive delete: prefix deny rules miss all of these ----
    ("Bash", "rm -rf ./src", "", 2, "rm -rf project dir"),
    ("Bash", "rm -fr ./src", "", 2, "rm -fr flag order swapped"),
    ("Bash", "rm -r -f ./src", "", 2, "rm -r -f flags split"),
    ("Bash", "rm -R ./src", "", 2, "rm -R capital"),
    ("Bash", "rm --recursive ./src", "", 2, "rm --recursive long form"),
    ("Bash", "cd x ; rm -rf y", "", 2, "rm not first token"),
    ("Bash", "npm test && rm -rf dist", "", 2, "rm after &&"),
    ("PowerShell", "Remove-Item -Recurse ./src", "", 2, "ps recursive"),
    ("PowerShell", "ri -r -fo ./src", "", 2, "ps abbreviated flags via alias ri"),
    ("PowerShell", "rm -Recurse -Force ./src", "", 2, "ps recursive via alias rm"),
    ("PowerShell", "npm test ; Remove-Item -Recurse x", "", 2, "ps recursive not first"),
    ("PowerShell", "Remove-Item -Recurse:$true x", "", 2, "ps -Recurse:$true form"),
    # ---- B4: the deny rule narrowed, so the hook is now the ONLY layer -------
    # The template deny rule went from PowerShell(Remove-Item:*) — which blocked
    # ordinary single-file deletion, an over-block — to
    # PowerShell(Remove-Item -Recurse:*). A deny rule is a PREFIX matcher, so the
    # narrowed rule only sees -Recurse when it is the FIRST argument. Every case
    # below puts it somewhere else, or spells it via an alias, and so is caught
    # by this hook alone. If the flag parser regresses, these go red and nothing
    # else is left standing.
    ("PowerShell", "Remove-Item -Force -Recurse ./src", "", 2,
     "B4: -Recurse behind -Force (deny prefix misses this)"),
    ("PowerShell", "Remove-Item ./src -Recurse", "", 2,
     "B4: -Recurse trailing (deny prefix misses this)"),
    ("PowerShell", "Remove-Item -Path ./src -Recurse -Force", "", 2,
     "B4: -Recurse after -Path (deny prefix misses this)"),
    ("PowerShell", "rd -Recurse ./src", "", 2, "B4: recursive via alias rd"),
    ("PowerShell", "erase -Recurse ./src", "", 2, "B4: recursive via alias erase"),
    # Single-file delete: must PASS. Over-blocking is a framework defect by the
    # handoff's own kill criteria, and this is the ALLOW half of the B4 pair.
    ("PowerShell", "Remove-Item ./one.txt", "", 0, "ps single-file delete allowed"),
    ("PowerShell", "Remove-Item -Force ./one.txt", "", 0, "ps -Force single file allowed"),
    ("PowerShell", "Remove-Item -Path ./one.txt -Force", "", 0,
     "B4: -Path single file allowed"),
    ("PowerShell", "del foo.txt", "", 0, "ps del single file allowed"),
    ("PowerShell", "ri ./one.txt", "", 0, "B4: single file via alias ri allowed"),
    # non-recursive single-file rm stays allowed: the bash deny list does not
    # cover it either, and blocking it would make the ALLOW column meaningless
    ("Bash", "rm file.txt", "", 0, "rm single file allowed"),
    ("Bash", "rm -f file.txt", "", 0, "rm -f single file allowed"),
    # ---- force push: every spelling ----
    ("Bash", "git push --force-with-lease", "", 2, "force-with-lease, no branch"),
    ("Bash", "git push --force-with-lease origin main", "", 2, "force-with-lease + main"),
    ("Bash", "git push --force-if-includes origin x", "", 2, "force-if-includes"),
    ("Bash", "git push origin +main", "", 2, "refspec force push"),
    ("Bash", "git push -f origin feature", "", 2, "short -f any branch"),
    ("PowerShell", "git push origin +main", "", 2, "ps refspec force push"),
    ("PowerShell", "git push --force-with-lease", "", 2, "ps force-with-lease"),
    ("Bash", "git push origin main", "", 0, "ordinary push allowed (ask-gated)"),
    ("Bash", "git push", "", 0, "bare push allowed (ask-gated)"),
    # ---- evaluator allowlist, Bash ----
    ("Bash", "npm test", "evaluator", 0, "eval bash npm test"),
    ("Bash", "git status", "evaluator", 0, "eval bash git status"),
    ("Bash", "git status --porcelain", "evaluator", 0, "eval bash porcelain"),
    ("Bash", "git log --oneline", "evaluator", 2, "eval bash git log blocked"),
    ("Bash", "echo x > src/a.ts", "evaluator", 2, "eval bash redirect blocked"),
    ("Bash", "python -c 'x'", "evaluator", 2, "eval bash non-allowlisted"),
    # ---- Step 0b: the evaluator shell self-probe -----------------------------
    # evaluator.md tells the evaluator to run this VERBATIM as its shell probe.
    # BLOCKED means shell containment is live and it continues; if it runs, the
    # evaluator must abort with P0 HARNESS FAILURE. Keep this string in sync with
    # the command in .claude/agents/evaluator.md -- the template's contract test
    # asserts the agent file still names it.
    ("Bash", "python -c \"print('evaluator shell probe')\"", "evaluator", 2,
     "eval STEP 0b shell probe blocked"),
    ("Bash", "python3 -c \"print('evaluator shell probe')\"", "evaluator", 2,
     "eval STEP 0b probe blocked, python3 spelling"),
    ("PowerShell", "python -c \"print('evaluator shell probe')\"", "evaluator", 2,
     "eval STEP 0b shell probe blocked, ps"),
    # The probe must be inert for everyone ELSE, or it is not a safe thing to
    # instruct: outside the evaluator it is an ordinary print and must pass. This
    # is also what proves the block above comes from the evaluator allowlist and
    # not from some unrelated rule matching the string.
    ("Bash", "python -c \"print('evaluator shell probe')\"", "", 0,
     "eval STEP 0b probe is inert outside the evaluator"),
    ("PowerShell", "python -c \"print('evaluator shell probe')\"", "", 0,
     "eval STEP 0b probe inert outside the evaluator, ps"),
    # ---- evaluator allowlist, PowerShell ----
    ("PowerShell", "npm test", "evaluator", 0, "eval ps npm test"),
    ("PowerShell", "git status", "evaluator", 0, "eval ps git status"),
    ("PowerShell", "git status --porcelain", "evaluator", 0, "eval ps porcelain"),
    ("PowerShell", "git log --oneline", "evaluator", 2, "eval ps git log blocked"),
    ("PowerShell", "Set-Content src/a.ts 'x'", "evaluator", 2, "eval ps write blocked"),
    ("PowerShell", "'x' > src/a.ts", "evaluator", 2, "eval ps redirect blocked"),
    ("PowerShell", "Invoke-Expression 'bad'", "evaluator", 2, "eval ps iex blocked"),
    ("PowerShell", "Get-Content src/a.ts", "evaluator", 0, "eval ps read allowed"),
    ("PowerShell", "python -c 'x'", "evaluator", 2, "eval ps non-allowlisted"),

    # ==== A3: evaluator context isolation on the SHELL side ===================
    # The evaluator keeps `cat`, so the agent-scoped Read hook is not enough.
    ("Bash", "cat docs/PROGRESS.md", "evaluator", 2, "eval shell PROGRESS blocked"),
    ("Bash", "cat session-context.md", "evaluator", 2, "eval shell session-context blocked"),
    ("Bash", "cat docs/evals/eval-01.md", "evaluator", 2, "eval shell prior evals blocked"),
    ("Bash", "grep -r x docs/evals/", "evaluator", 2, "eval shell grep evals blocked"),
    ("PowerShell", "Get-Content docs\\PROGRESS.md", "evaluator", 2, "eval shell PROGRESS blocked ps"),
    ("PowerShell", "Get-Content session-context.md", "evaluator", 2, "eval shell session-context blocked ps"),
    ("PowerShell", "Get-Content docs\\evals\\eval-01.md", "evaluator", 2, "eval shell evals blocked ps"),
    ("Bash", "cat docs/SPEC.md", "evaluator", 0, "eval SPEC.md allowed"),
    ("Bash", "cat src/index.ts", "evaluator", 0, "eval source allowed"),
    # The same commands outside the evaluator are ordinary work.
    ("Bash", "cat docs/PROGRESS.md", "", 0, "PROGRESS readable outside evaluator"),
    ("Bash", "cat docs/evals/eval-01.md", "", 0, "evals readable outside evaluator"),
]

# Labels that MUST turn red when git-global normalization is disabled, and
# nothing else may move. Anything blocked by a different mechanism (the
# hooks-path policy, the fail-closed parser, quoted-value blanking) belongs
# outside this set — including it would hide which mechanism does the work.
#
# Three BLOCK cases are deliberately NOT listed, because the mutant still
# catches them and it would be false to claim normalization is what protects
# them:
#   gg GIT_DIR reset / gg GIT_WORK_TREE checkout — a leading NAME=VALUE does
#     not break `git <verb>` adjacency, so the plain rule matches either way.
#   gg spaced --git-dir reset — the path text `...\.git reset --hard` contains
#     the pattern by coincidence. That coincidence IS the pre-fix false
#     positive; `gg spaced --git-dir reset no-dotgit` is the same command
#     without it and does discriminate.
MUTATION_EXPECT_RED = {
    "gg -C reset", "gg -C reset ps", "gg -c reset", "gg --git-dir= reset",
    "gg --git-dir space reset", "gg --work-tree checkout", "gg -C clean",
    "gg -C push force", "gg -C push refspec", "gg -C no-verify", "gg -C -n",
    # NOTE: "gg -C restore" is deliberately NOT in this set any more. It used to
    # be, because restore was matched by a GIT_RULES regex over the normalized
    # string. It is now caught by check_git_restore(), which reads the parsed
    # token list directly and so does not depend on normalization at all —
    # `git -C repo restore .` still BLOCKS, it just no longer goes red when
    # normalization is disabled. Strictly more robust, hence one fewer case here.
    "gg stacked globals reset", "gg spaced -C reset",
    "gg spaced -C reset ps", "gg spaced --git-dir reset no-dotgit",
    "gg spaced --work-tree checkout", "gg spaced --work-tree checkout ps",
    "gg chained reset", "gg chained reset ps", "gg substitution reset",
    "gg backtick reset",
    # B4 added this case; it is a global-option destructive form like the rest,
    # so normalization is exactly what catches it.
    "B4 BLOCK: --hard behind -C",
}

# --- Session B mutations -----------------------------------------------------
# Same contract as the A1 mutation above: disable ONE narrowly-scoped behaviour
# and assert that EXACTLY a named set of cases turns red. The B guards narrowed
# what the permission deny-rules block, which makes this hook the only remaining
# layer for several forms — so "the test suite still passes" is not evidence on
# its own. These say which line is doing the catching.
#
# (key, description, anchor, patch, expected-red labels)
MUTATIONS = [
    (
        "a1-git-globals",
        "git-global normalization disabled",
        MUTATION_ANCHOR,
        MUTATION_PATCH,
        MUTATION_EXPECT_RED,
    ),
    (
        "b3-env-carveout",
        "B3: the .env.example/.sample/.template carve-out restored",
        'ENVFILE = r"\\.env"',
        'ENVFILE = r"\\.env(?!\\.example|\\.sample|\\.template)"',
        {
            "ps .env.example now blocked (B3)",
            "bash .env.sample now blocked (B3)",
            "bash .env.template now blocked (B3)",
        },
    ),
    (
        "b4-git-reset",
        "B4: git reset reverted to the old blanket block",
        '(r"git\\s+reset\\s+--hard",',
        '(r"git\\s+reset\\b",',
        {
            "B4 ALLOW: reset HEAD file (unstage)",
            "B4 ALLOW: reset HEAD file, ps",
            "B4 ALLOW: unstage a path",
            "B4 ALLOW: bare reset (unstage all)",
            "B4 ALLOW: reset --mixed",
            "reset --soft allowed",
        },
    ),
    (
        "b4-restore-off",
        "git-restore tree check disabled entirely",
        '    if not rest or rest[0][0].lower() != "restore":',
        '    if True:',
        {
            "bash restore .", "ps restore .", "gg -C restore",
            "restore of a dotfile WITHOUT --staged still blocked",
            "restore of one file discards its edits - was silently ALLOWED before",
            "explicit --worktree blocked even on a dotfile",
            "--staged does not excuse an explicit --worktree",
            "short -W blocked",
            "combined -SW still writes the worktree",
            "-s is --source, NOT --staged: must still block",
            "-- separator without --staged still blocked",
            "restore after && still blocked",
            "restore after ; still blocked, ps",
        },
    ),
    (
        "b4-restore-staged-blind",
        "--staged no longer recognised (re-creates the dotfile over-block)",
        '            if name == "--staged":',
        '            if False:',
        {
            "restore --staged dotfile allowed (was the over-block)",
            "restore --staged dotted dir allowed (was the over-block)",
            "restore --staged dotfile allowed, ps",
            "restore --staged ordinary path allowed",
            "restore --staged . unstages all, working tree untouched",
            "restore --staged glob allowed",
            "restore --staged with -- separator allowed",
        },
    ),
    (
        "eval-shell-allowlist-off",
        "evaluator shell allowlist disabled (the Step 0b SUCCEEDS branch)",
        "        if head not in allowed:",
        "        if False:",
        {
            "eval bash non-allowlisted",
            "eval ps non-allowlisted",
            "eval STEP 0b shell probe blocked",
            "eval STEP 0b probe blocked, python3 spelling",
            "eval STEP 0b shell probe blocked, ps",
        },
    ),
    (
        "b4-ps-recursive",
        "B4: the PowerShell recursive-delete flag scan disabled",
        '        if head == "remove-item":',
        '        if False:',
        {
            "ps recursive delete",
            "ps recursive delete via alias ri",
            "ps recursive",
            "ps abbreviated flags via alias ri",
            "ps recursive via alias rm",
            "ps recursive not first",
            "ps -Recurse:$true form",
            "B4: -Recurse behind -Force (deny prefix misses this)",
            "B4: -Recurse trailing (deny prefix misses this)",
            "B4: -Recurse after -Path (deny prefix misses this)",
            "B4: recursive via alias rd",
            "B4: recursive via alias erase",
        },
    ),
]


def run(guard, tool, cmd, agent):
    payload = {"tool_name": tool, "tool_input": {"command": cmd}}
    if agent:
        payload["agent_type"] = agent
    p = subprocess.run([sys.executable, guard],
                       input=json.dumps(payload), capture_output=True, text=True)
    return p.returncode, (p.stderr or "").strip()


def results(guard):
    """-> {label: passed?}"""
    out = {}
    for tool, cmd, agent, want, label in CASES:
        got, _err = run(guard, tool, cmd, agent)
        out[label] = (got == want)
    return out


def normal():
    failures = []
    for tool, cmd, agent, want, label in CASES:
        got, err = run(GUARD, tool, cmd, agent)
        if got != want:
            failures.append((label, tool, cmd, want, got, err[:120]))
    total = len(CASES)
    print(f"{total - len(failures)}/{total} passed")
    if failures:
        print("\nFAILURES:")
        for label, tool, cmd, want, got, err in failures:
            print(f"  [{label}] {tool}: {cmd!r}")
            print(f"      want exit {want}, got {got}. stderr: {err}")
        return 1
    return 0


def mutate_one(src, baseline, key, desc, anchor, patch, expect_red):
    if src.count(anchor) != 1:
        print(f"[{key}] MUTATION SETUP FAILED: anchor not found exactly once:")
        print(f"        {anchor!r}")
        return 1

    fd, mutant = tempfile.mkstemp(suffix="_mutant.py", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(src.replace(anchor, patch, 1))
        after = results(mutant)
    finally:
        os.unlink(mutant)

    went_red = {l for l, ok in after.items() if not ok}
    missing = expect_red - went_red   # the fix is not what catches these
    extra = went_red - expect_red     # collateral: something else moved

    print(f"[{key}] mutation: {desc}")
    print(f"        expected red: {len(expect_red)}   actually red: {len(went_red)}")
    ok = True
    if missing:
        ok = False
        print("\n        STILL PASSING under the mutation — these cases are not")
        print("        actually protected by the code they are supposed to test:")
        for l in sorted(missing):
            print(f"          {l}")
    if extra:
        ok = False
        print("\n        UNEXPECTEDLY red — the mutated code is load-bearing for")
        print("        cases outside the named set, so this proves less than claimed:")
        for l in sorted(extra):
            print(f"          {l}")
    if ok:
        print("        exactly the named set turned red; every other case held.")
    print()
    return 0 if ok else 1


def mutate():
    src = open(GUARD, encoding="utf-8").read()

    baseline = results(GUARD)
    unhealthy = sorted(l for l, ok in baseline.items() if not ok)
    if unhealthy:
        print("Run the normal suite first — it is not green:")
        for l in unhealthy:
            print(f"  {l}")
        return 1

    rc = 0
    for key, desc, anchor, patch, expect_red in MUTATIONS:
        rc |= mutate_one(src, baseline, key, desc, anchor, patch, expect_red)

    print("ALL MUTATIONS PASSED" if rc == 0 else "MUTATION FAILURES ABOVE")
    return rc


if __name__ == "__main__":
    sys.exit(mutate() if "--mutate" in sys.argv else normal())
