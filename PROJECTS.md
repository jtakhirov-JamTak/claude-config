# Active projects

Moved out of CLAUDE.md deliberately: this changes as projects start, ship, and
retire, and a file re-read at the start of every session should hold rules, not
inventory.

Visibility is in the table because it changes what "safe to commit" means: in a public
repo a committed secret is world-readable the moment it lands, with no recall. Four of
these are public, including the one with users and this config set itself.

| Path | What it is | Visibility | State |
|---|---|---|---|
| `pure-eq` | Insights app | **PUBLIC** | **Live — the only shipped app, and the only one with users.** |
| `the-leaf-v2` | Leaf — the main product | Private | In build; MVP polish, first workshop April 2026 |
| `dev\agentic-template-v4` | The GitHub template every new app is scaffolded from, via `new-app.ps1` | **PUBLIC** | Stable. Carries `/interview`, the evaluator agent, and `write_guard.py` / `evaluator_guard.py` — **none of which exist in `~/.claude`**. Check here before concluding that a reference from this config set is dangling. |
| `you-inc` | Scoring + pricing app | **PUBLIC** | Early |
| `PurePath` | Habit / sprint app | Private | Early |
| `~/.claude` (`claude-config`) | This config set — rules, commands, hooks, scaffold | **PUBLIC** | Everything committed here is world-readable, including settings history. |
| `dev\app-foundation` | Shared scaffolding / reference architecture | — | **Not found, checked 2026-08-25:** no repo of that name on the account and no local directory. Treat as retired until confirmed. |

All are pushed to `github.com/jtakhirov-JamTak`. Only `pure-eq` has users, so "is this
safe to ship" means something stricter there than in the rest.

There is also a private `TheLeaf` repo on the account, not listed above because its
relationship to `the-leaf-v2` is unconfirmed.
