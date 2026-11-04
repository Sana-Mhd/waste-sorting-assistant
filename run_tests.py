"""Run the test suites of all four subsystems with one command.

Each subsystem has its own conftest.py, so each suite runs from its own folder.

    python run_tests.py
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUBSYSTEMS = ("classification", "data_rules", "coach", "web")


def run_suite(subsystem: str) -> tuple[bool, str]:
    """Run one test suite.

    Args:
        subsystem: the folder of the subsystem, e.g. "web".

    Returns:
        Whether every test passed, and pytest's last line (the totals).
    """
    print(f"\n===== {subsystem} =====", flush=True)
    process = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--color=no"],
        cwd=ROOT / subsystem, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    print(process.stdout)
    print(process.stderr, file=sys.stderr)
    # If pytest could not start, stdout is empty and the reason is in stderr.
    lines = (process.stdout.strip() or process.stderr.strip()).splitlines()
    return process.returncode == 0, lines[-1] if lines else "pytest gave no output"


def main() -> int:
    """Run every suite and print a summary. Returns the exit code: 0 only if all passed."""
    results = {subsystem: run_suite(subsystem) for subsystem in SUBSYSTEMS}

    print("\n===== summary =====")
    for subsystem, (passed, totals) in results.items():
        print(f"{'PASS' if passed else 'FAIL'}  {subsystem:15} {totals}")
    return 0 if all(passed for passed, _ in results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
