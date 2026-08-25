#!/usr/bin/env python
"""Claude Code statusline — context percentage only.

Replaces statusline.ps1, which spawned a PowerShell process and shelled out to git on
every render to print seven fields. Only one of them was load-bearing: the context
percentage, because it is the trigger for /save-context.

Reads the session JSON payload on stdin, writes one line to stdout.
Thresholds match the /save-context trigger: yellow at 45%, red at 60%.

Anything unreadable — no stdin, bad JSON, missing key, null value — renders as 0% rather
than raising. A statusline that crashes takes the status bar down every turn.
"""

import json
import sys

YELLOW_AT = 45
RED_AT = 60

RESET = "\033[0m"
YELLOW = "\033[33m"
RED = "\033[31m"


def read_percent() -> int:
    try:
        payload = json.loads(sys.stdin.read())
        pct = int(float(payload["context_window"]["used_percentage"]))
    except Exception:
        return 0
    return max(0, min(100, pct))


def main() -> None:
    pct = read_percent()
    if pct >= RED_AT:
        sys.stdout.write("{}Context {}%{}".format(RED, pct, RESET))
    elif pct >= YELLOW_AT:
        sys.stdout.write("{}Context {}%{}".format(YELLOW, pct, RESET))
    else:
        sys.stdout.write("Context {}%".format(pct))


if __name__ == "__main__":
    main()
