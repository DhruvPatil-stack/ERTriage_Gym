"""Build the run plan from smoke test latencies.

The plan lists every planned run and its time estimate.
Drops happen from the end until the total fits the budget.
"""
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from eval.eval_config import MAX_RUN_HOURS  # noqa: E402


TEST_ITEMS = 208
CONDITIONS = ["rules", "plain"]
LOAD_SECONDS = 60


def _load_smoke():
    """Return the smoke result map, or an empty dict if missing."""
    path = _HERE / "reports" / "smoke_results.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _format_row(rid, adapter, split, cond, items, mins, planned):
    """Format one row of the plan table."""
    if isinstance(mins, (int, float)):
        mins_s = f"{mins:>12.1f}"
    else:
        mins_s = f"{mins:>12}"
    if isinstance(items, (int, float)):
        items_s = f"{items:>9}"
    else:
        items_s = f"{items:>9}"
    return (
        f"{rid:<60} | {adapter:<20} | {split:<4} | {cond:<5} | "
        f"{items_s} | {mins_s} | {planned:<3}"
    )


def main():
    smoke = _load_smoke()
    if not smoke:
        print("No smoke results. Writing plan with no model runs.")
    budget_s = MAX_RUN_HOURS * 3600

    # Build full list of candidate rows.
    rows = []
    for model, data in smoke.items():
        for cond in CONDITIONS:
            med = data.get("median_s", 0.0)
            est_s = med * TEST_ITEMS + LOAD_SECONDS
            safe_name = model.replace(":", "-").replace("/", "-")
            rid = f"{safe_name}_{cond}_test_PLANNED"
            rows.append({
                "run_id": rid,
                "adapter": model,
                "split": "test",
                "condition": cond,
                "items": TEST_ITEMS,
                "est_s": est_s,
            })

    # Mark planned yes until budget runs out. Drop from the end.
    total = 0.0
    for r in rows:
        if total + r["est_s"] <= budget_s:
            r["planned"] = "yes"
            total += r["est_s"]
        else:
            r["planned"] = "no"

    lines = [
        "ESI run plan",
        "------------",
        f"budget_hours: {MAX_RUN_HOURS}",
        f"total_minutes_planned: {total/60:.1f}",
        "",
        _format_row("run_id", "adapter", "spl", "cond", "est_items", "est_time_min", "yes/no"),
        "-" * 120,
    ]
    for r in rows:
        lines.append(_format_row(
            r["run_id"], r["adapter"], r["split"], r["condition"],
            r["items"], r["est_s"] / 60.0, r["planned"],
        ))

    out = _HERE / "reports" / "run_plan.txt"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"Wrote {out}")

    # Record drops with a reason.
    dropped = [r for r in rows if r["planned"] == "no"]
    if dropped:
        drop_path = _HERE / "reports" / "dropped_runs.txt"
        with drop_path.open("w", encoding="utf-8") as f:
            f.write("The following runs were dropped. Reason: time budget.\n")
            for r in dropped:
                f.write(f"{r['run_id']}  est_min={r['est_s']/60:.1f}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
