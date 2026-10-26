"""Run every planned entry from run_plan.txt.

The script parses the run plan and calls run_eval.run for each row.
Progress goes to eval/reports/run_log.txt.
"""
import datetime
import json
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from eval.run_eval import run as run_eval_run  # noqa: E402


def _parse_plan():
    """Return the list of planned runs from run_plan.txt."""
    path = _HERE / "reports" / "run_plan.txt"
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        if line.lower().startswith("run_id"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 7:
            continue
        rid, adapter, split, cond, est_items, est_min, planned = parts[:7]
        if planned.lower() != "yes":
            continue
        rows.append({
            "run_id": rid,
            "adapter": adapter,
            "split": split,
            "condition": cond,
            "est_items": est_items,
            "est_min": est_min,
        })
    return rows


def _append_log(msg):
    """Append a line to the run log."""
    path = _HERE / "reports" / "run_log.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.utcnow().isoformat() + "Z"
    with path.open("a", encoding="utf-8") as f:
        f.write(f"[{stamp}] {msg}\n")


def main():
    plan = _parse_plan()
    if not plan:
        print("No planned runs. Check run_plan.txt.")
        return 1
    _append_log(f"start of batch: {len(plan)} planned runs")
    for i, row in enumerate(plan, start=1):
        _append_log(f"begin {i}/{len(plan)}: {row['run_id']}")
        print(f"[{i}/{len(plan)}] {row['run_id']}")
        try:
            code = run_eval_run(
                split=row["split"],
                condition=row["condition"],
                adapter_name=row["adapter"],
                allow_test=(row["split"] == "test"),
                run_id=row["run_id"],
            )
            _append_log(f"end {row['run_id']} code={code}")
        except Exception as e:
            _append_log(f"ERROR {row['run_id']}: {e}")
            print(f"ERROR: {e}")
    _append_log("batch complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
