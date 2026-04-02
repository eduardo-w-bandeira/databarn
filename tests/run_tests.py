from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    tests_dir = Path(__file__).resolve().parent
    repo_root = tests_dir.parent
    command = [sys.executable, "-m", "pytest", str(tests_dir)]
    completed = subprocess.run(command, cwd=repo_root)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())