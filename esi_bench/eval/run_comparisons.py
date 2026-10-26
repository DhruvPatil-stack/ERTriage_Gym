"""Run all required pairwise compare.py checks.

Pairs: rules vs plain per model, then model vs model under rules.
Output goes to eval/reports/comparisons.txt.
"""
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from eval.compare import compare as compare_runs  # noqa: E402


def _collect_test_runs():
    """Return a dict grouping test runs by (adapter, condition)."""
    runs_dir = _HERE / "runs"
    out = {}
    if not runs_dir.exists():
        return out
    for rd in sorted(runs_dir.iterdir()):
        if not rd.is_dir():
            continue
        meta = rd / "results.json"
        if not meta.exists():
            continue
        try:
            m = json.loads(meta.read_text(encoding="utf-8"))
        except Exception:
            continue
        if m.get("split") != "test":
            continue
        key = (m["adapter"], m["condition"])
        # Keep the newest only.
        out.setdefault(key, rd.name)
    return out


def main():
    runs = _collect_test_runs()
    if not runs:
        print("No test runs. Nothing to compare.")
        return 0

    out_lines = ["ESI pairwise comparisons", "------------------------", ""]
    # Rules vs plain per adapter.
    adapters = sorted({a for a, c in runs.keys()})
    out_lines.append("## Rules vs plain per adapter")
    for a in adapters:
        rid_r = runs.get((a, "rules"))
        rid_p = runs.get((a, "plain"))
        if rid_r and rid_p:
            buf = io.StringIO()
            with redirect_stdout(buf):
                compare_runs(rid_r, rid_p)
            out_lines.append(f"\n### {a}: rules vs plain")
            out_lines.append(buf.getvalue())

    # Model vs model under rules.
    rules_adapters = sorted([a for a, c in runs.keys() if c == "rules"])
    out_lines.append("\n## Model pairs under rules")
    for i in range(len(rules_adapters)):
        for j in range(i + 1, len(rules_adapters)):
            a = rules_adapters[i]
            b = rules_adapters[j]
            rid_a = runs[(a, "rules")]
            rid_b = runs[(b, "rules")]
            buf = io.StringIO()
            with redirect_stdout(buf):
                compare_runs(rid_a, rid_b)
            out_lines.append(f"\n### {a} vs {b}")
            out_lines.append(buf.getvalue())

    out = _HERE / "reports" / "comparisons.txt"
    out.write_text("\n".join(out_lines), encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
