"""Run every Phase D step in order.

Order: analyze.py, run_comparisons.py, make_summary.py, security_check.py,
checksums_after.py. Each step runs even if an earlier step fails.
"""
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _run(script):
    """Run one script with py and print status."""
    print(f"\n--- {script} ---")
    res = subprocess.run(["py", str(_HERE / script)], capture_output=True, text=True)
    sys.stdout.write(res.stdout)
    if res.returncode != 0:
        print(f"FAIL {script}: exit={res.returncode}")
        sys.stdout.write(res.stderr)
    return res.returncode


def main():
    _run("analyze.py")
    _run("run_comparisons.py")
    _run("make_summary.py")
    _run("security_check.py")
    _run("checksums_after.py")
    print("\nFinalize complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
