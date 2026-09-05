#!/usr/bin/env python3
"""Run one command with a process-group timeout and preserve its output."""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys


def stop_group(process: subprocess.Popen[str]) -> None:
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
        process.communicate(timeout=3)
    except (OSError, subprocess.TimeoutExpired):
        try:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
            process.communicate(timeout=3)
        except (OSError, subprocess.TimeoutExpired):
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, required=True)
    args, command = parser.parse_known_args()
    if command[:1] == ["--"]:
        command = command[1:]
    if not command:
        parser.error("a command is required after --")

    process = subprocess.Popen(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=(os.name == "posix"),
    )
    try:
        output, _ = process.communicate(timeout=args.timeout)
    except subprocess.TimeoutExpired as error:
        output = error.output or ""
        stop_group(process)
        if not isinstance(output, str):
            output = output.decode(errors="replace")
        print(output[-8000:], end="" if output.endswith("\n") else "\n")
        print(f"bounded command timed out after {args.timeout:g}s: {' '.join(command)}", file=sys.stderr)
        return 124
    print(output, end="")
    return process.returncode


if __name__ == "__main__":
    raise SystemExit(main())
