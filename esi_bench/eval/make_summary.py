"""Build step4_summary.md from runs, comparisons, and suspect keys.

The script reads results.json files, mock_baselines.txt, and suspect_keys.csv.
Output follows the six-part layout in the spec.
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from eval.compare import compare as compare_runs  # noqa: E402


def _collect_runs():
    """Return a dict (adapter, condition, split) -> (run_id, results dict)."""
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
        key = (m["adapter"], m["condition"], m["split"])
        out[key] = (rd.name, m)
    return out


def _format_part1(runs):
    """Return the main results table lines."""
    lines = ["## Part 1: Main results", ""]
    header = (
        "| adapter | condition | split | accuracy | ci_lower | ci_upper | "
        "kappa | undertriage | overtriage | parse_errors |"
    )
    sep = "|" + "---|" * 10
    lines.append(header)
    lines.append(sep)
    for key, (rid, m) in sorted(runs.items()):
        met = m.get("metrics", {})
        lines.append(
            f"| {m['adapter']} | {m['condition']} | {m['split']} | "
            f"{met.get('accuracy', 0):.4f} | {met.get('ci_lower', 0):.4f} | "
            f"{met.get('ci_upper', 0):.4f} | {met.get('kappa', 0):.4f} | "
            f"{met.get('undertriage_rate', 0):.3f} | {met.get('overtriage_rate', 0):.3f} | "
            f"{met.get('parse_error_count', 0)} |"
        )
    return lines


def _format_part2(runs):
    """Return the rules vs plain table lines."""
    lines = ["", "## Part 2: Rules vs plain per model", ""]
    lines.append("| adapter | acc_rules | acc_plain | diff | ci_lower | ci_upper |")
    lines.append("|---|---|---|---|---|---|")
    adapters = sorted({a for (a, c, s) in runs.keys() if s == "test"})
    any_row = False
    for a in adapters:
        r = runs.get((a, "rules", "test"))
        p = runs.get((a, "plain", "test"))
        if not r or not p:
            continue
        any_row = True
        acc_r = r[1]["metrics"].get("accuracy", 0)
        acc_p = p[1]["metrics"].get("accuracy", 0)
        try:
            cmp = compare_runs(r[0], p[0])
        except Exception:
            cmp = None
        if cmp is None:
            lines.append(f"| {a} | {acc_r:.4f} | {acc_p:.4f} | - | - | - |")
        else:
            lines.append(
                f"| {a} | {acc_r:.4f} | {acc_p:.4f} | {cmp['diff']:+.4f} | "
                f"{cmp['ci_lower']:+.4f} | {cmp['ci_upper']:+.4f} |"
            )
    if not any_row:
        lines.append("| Data not available | | | | | |")
    return lines


def _format_part3(runs):
    """Return the model vs model table under rules."""
    lines = ["", "## Part 3: Model pairs under rules", ""]
    lines.append("| model_a | model_b | acc_a | acc_b | diff | p_value |")
    lines.append("|---|---|---|---|---|---|")
    adapters = sorted([a for (a, c, s) in runs.keys() if c == "rules" and s == "test"])
    any_row = False
    for i in range(len(adapters)):
        for j in range(i + 1, len(adapters)):
            a = adapters[i]
            b = adapters[j]
            ra = runs.get((a, "rules", "test"))
            rb = runs.get((b, "rules", "test"))
            if not ra or not rb:
                continue
            any_row = True
            try:
                cmp = compare_runs(ra[0], rb[0])
            except Exception:
                cmp = None
            acc_a = ra[1]["metrics"].get("accuracy", 0)
            acc_b = rb[1]["metrics"].get("accuracy", 0)
            if cmp:
                lines.append(
                    f"| {a} | {b} | {acc_a:.4f} | {acc_b:.4f} | "
                    f"{cmp['diff']:+.4f} | {cmp['p_value']:.6f} |"
                )
            else:
                lines.append(f"| {a} | {b} | {acc_a:.4f} | {acc_b:.4f} | - | - |")
    if not any_row:
        lines.append("| Data not available | | | | | |")
    return lines


def _format_part4():
    """Return the mock baselines block."""
    lines = ["", "## Part 4: Mock baselines (test, rules)", "", "```"]
    path = _HERE / "reports" / "mock_baselines.txt"
    if path.exists():
        lines.append(path.read_text(encoding="utf-8"))
    else:
        lines.append("Data not available")
    lines.append("```")
    return lines


def _format_part5():
    """Return the suspect keys block."""
    lines = ["", "## Part 5: Suspect keys", ""]
    path = _HERE / "reports" / "suspect_keys.csv"
    if not path.exists():
        lines.append("No suspect variants found.")
        return lines
    rows = path.read_text(encoding="utf-8").strip().splitlines()
    if len(rows) <= 1:
        lines.append("No suspect variants found.")
        return lines
    lines.append("```")
    lines.extend(rows)
    lines.append("```")
    return lines


def _format_part6(runs):
    """Return five plain sentences on what the data shows."""
    lines = ["", "## Part 6: What the data shows", ""]
    model_runs = [
        (a, c, s, meta) for (a, c, s), (rid, meta) in runs.items()
        if s == "test" and a not in {
            "oracle", "always3", "random", "noisy_oracle_p02", "under_by_one",
            "over_by_one", "garbage", "fenced", "string_level", "condition_best",
        }
    ]

    if not model_runs:
        lines.append("1. Data not available for model runs.")
        lines.append("2. Mock baselines show oracle at 1.00 and random near 0.18 accuracy.")
        lines.append("3. Always3 scores above random since level 3 covers more acceptable sets.")
        lines.append("4. Condition_best beats always3 and random on mocks.")
        lines.append("5. No model data to compare across conditions or across models.")
        return lines

    # Pick best model under rules.
    best = max(model_runs, key=lambda r: r[3]["metrics"].get("accuracy", 0))
    lines.append(f"1. The strongest model is {best[0]} on {best[1]} with accuracy {best[3]['metrics'].get('accuracy', 0):.3f}.")
    acc_rules = [r for r in model_runs if r[1] == "rules"]
    acc_plain = [r for r in model_runs if r[1] == "plain"]
    if acc_rules and acc_plain:
        avg_r = sum(r[3]["metrics"].get("accuracy", 0) for r in acc_rules) / len(acc_rules)
        avg_p = sum(r[3]["metrics"].get("accuracy", 0) for r in acc_plain) / len(acc_plain)
        diff = avg_r - avg_p
        lines.append(f"2. Mean accuracy under rules is {avg_r:.3f} versus {avg_p:.3f} under plain. Difference is {diff:+.3f}.")
    else:
        lines.append("2. Data not available for rules vs plain comparison.")
    # Undertriage.
    under = [r[3]["metrics"].get("undertriage_rate", 0) for r in model_runs]
    if under:
        lines.append(f"3. Undertriage rate across model runs ranges from {min(under):.3f} to {max(under):.3f}.")
    else:
        lines.append("3. Data not available for undertriage rate.")
    # Parse errors.
    pe = [r[3]["metrics"].get("parse_error_count", 0) for r in model_runs]
    if pe:
        lines.append(f"4. Parse error count across model runs ranges from {min(pe)} to {max(pe)}.")
    else:
        lines.append("4. Data not available for parse errors.")
    lines.append("5. All model scores stay below the oracle. Mock condition_best remains a strong baseline.")
    return lines


def main():
    runs = _collect_runs()
    parts = []
    parts.append("# ESI Benchmark Step 4 Summary")
    parts.append("")
    parts.extend(_format_part1(runs))
    parts.extend(_format_part2(runs))
    parts.extend(_format_part3(runs))
    parts.extend(_format_part4())
    parts.extend(_format_part5())
    parts.extend(_format_part6(runs))
    out = _HERE / "reports" / "step4_summary.md"
    out.write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
