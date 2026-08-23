#!/usr/bin/env python3
"""Regression test for shell_guard.py.

Run: python scripts/hooks/test_shell_guard.py

Each case names the exit code it must produce. BLOCK cases must exit 2; ALLOW
cases must exit 0. A rule that stops firing turns its BLOCK case red; a rule
that over-matches turns an ALLOW case red. Both directions are represented, so
a pass means something. Add a case here before changing any pattern.
"""
import json
import os
import subprocess
import sys

GUARD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shell_guard.py")

# (tool, command, agent, expect_exit, label)
CASES = [
    # ---- git rules, Bash ----
    ("Bash", "git commit --no-verify -m x", "", 2, "bash --no-verify"),
    ("Bash", "git commit -n -m x", "", 2, "bash -n shorthand"),
    ("Bash", "git config core.hooksPath /tmp/x", "", 2, "bash hooksPath"),
    ("Bash", "git reset --hard HEAD~1", "", 2, "bash reset --hard"),
    ("Bash", "git clean -fd", "", 2, "bash clean -f"),
    ("Bash", "git checkout -- .", "", 2, "bash checkout --"),
    ("Bash", "git restore .", "", 2, "bash restore ."),
    ("Bash", "npm test && git reset --hard", "", 2, "bash chained reset"),
    # ---- git rules, PowerShell (the coverage gap this fixes) ----
    ("PowerShell", "git commit --no-verify -m x", "", 2, "ps --no-verify"),
    ("PowerShell", "git commit -n -m x", "", 2, "ps -n shorthand"),
    ("PowerShell", "git config core.hooksPath C:/tmp/x", "", 2, "ps hooksPath"),
    ("PowerShell", "git reset --hard HEAD~1", "", 2, "ps reset --hard"),
    ("PowerShell", "git clean -fd", "", 2, "ps clean -f"),
    ("PowerShell", "git restore .", "", 2, "ps restore ."),
    ("PowerShell", "npm test ; git reset --hard", "", 2, "ps chained reset"),
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
    ("PowerShell", "Get-Content .env.example", "", 0, "ps read .env.example"),
    ("Bash", "cat .env.sample", "", 0, "bash read .env.sample"),
    ("PowerShell", "Get-Content .env.local", "", 2, "ps .env.local still blocked"),
    ("Bash", "cat .env.production", "", 2, "bash .env.production still blocked"),
    ("Bash", "npm test", "", 0, "bash npm test"),
    ("Bash", "git status", "", 0, "bash git status"),
    ("Bash", "git commit -m 'feat: add thing'", "", 0, "bash ordinary commit"),
    ("Bash", "cat src/index.ts", "", 0, "bash read source"),
    ("Bash", "cat .env.example", "", 0, "bash read .env.example"),
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
    # Single-file delete: hook allows, symmetric with bash `rm file.txt`. The
    # template's PowerShell(Remove-Item:*) deny rule is the stricter layer, and
    # the CLAUDE.md hard stop governs it behaviourally everywhere else.
    ("PowerShell", "Remove-Item ./one.txt", "", 0, "ps single-file delete allowed"),
    ("PowerShell", "Remove-Item -Force ./one.txt", "", 0, "ps -Force single file allowed"),
    ("PowerShell", "del foo.txt", "", 0, "ps del single file allowed"),
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
    ("Bash", "git log --oneline", "evaluator", 2, "eval bash git log blocked"),
    ("Bash", "echo x > src/a.ts", "evaluator", 2, "eval bash redirect blocked"),
    ("Bash", "python -c 'x'", "evaluator", 2, "eval bash non-allowlisted"),
    # ---- evaluator allowlist, PowerShell (previously absent entirely) ----
    ("PowerShell", "npm test", "evaluator", 0, "eval ps npm test"),
    ("PowerShell", "git status", "evaluator", 0, "eval ps git status"),
    ("PowerShell", "git log --oneline", "evaluator", 2, "eval ps git log blocked"),
    ("PowerShell", "Set-Content src/a.ts 'x'", "evaluator", 2, "eval ps write blocked"),
    ("PowerShell", "'x' > src/a.ts", "evaluator", 2, "eval ps redirect blocked"),
    ("PowerShell", "Invoke-Expression 'bad'", "evaluator", 2, "eval ps iex blocked"),
    ("PowerShell", "Get-Content src/a.ts", "evaluator", 0, "eval ps read allowed"),
    ("PowerShell", "python -c 'x'", "evaluator", 2, "eval ps non-allowlisted"),
]


def run(tool, cmd, agent):
    payload = {"tool_name": tool, "tool_input": {"command": cmd}}
    if agent:
        payload["agent_type"] = agent
    p = subprocess.run([sys.executable, GUARD],
                       input=json.dumps(payload), capture_output=True, text=True)
    return p.returncode, (p.stderr or "").strip()


def main():
    failures = []
    for tool, cmd, agent, want, label in CASES:
        got, err = run(tool, cmd, agent)
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


if __name__ == "__main__":
    sys.exit(main())
