"""Compare two run outputs with a paired bootstrap and a McNemar test.

The script loads responses from two runs, pairs by id, and prints the diff.
Fails if the id sets differ.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from eval.eval_config import BOOTSTRAP_N, BOOTSTRAP_SEED  # noqa: E402


def load_jsonl(path: Path):
    """Return a list of dicts from a JSONL file."""
    out = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def _results_dir(run_id: str) -> Path:
    """Return the run folder."""
    return _HERE / "runs" / run_id


def _load_run(run_id: str):
    """Load responses and the split key file for a run."""
    rdir = _results_dir(run_id)
    responses = load_jsonl(rdir / "responses.jsonl")
    # Need the key file to grade. Load from results.json.
    results = json.loads((rdir / "results.json").read_text(encoding="utf-8"))
    split = results["split"]
    keys = load_jsonl(_HERE / "data" / f"{split}_key.jsonl")
    keys_dict = {k["id"]: k for k in keys}
    return responses, keys_dict


def _correct_flag(resp, keys_dict):
    """Return 1 if the response is correct, else 0."""
    if resp.get("status") != "ok" or resp.get("level") is None:
        return 0
    ans = int(resp["level"])
    accept = [int(x) for x in keys_dict[resp["id"]]["acceptable_levels"]]
    return 1 if ans in accept else 0


def paired_bootstrap(a_flags, b_flags, n=BOOTSTRAP_N, seed=BOOTSTRAP_SEED):
    """Return (diff_point, ci_lower, ci_upper) for acc_a minus acc_b."""
    a = np.array(a_flags, dtype=int)
    b = np.array(b_flags, dtype=int)
    size = len(a)
    rng = np.random.default_rng(seed)
    diffs = np.empty(n, dtype=float)
    for i in range(n):
        idx = rng.integers(0, size, size)
        diffs[i] = a[idx].mean() - b[idx].mean()
    diff_point = float(a.mean() - b.mean())
    lower = float(np.percentile(diffs, 2.5))
    upper = float(np.percentile(diffs, 97.5))
    return diff_point, lower, upper


def mcnemar_exact(a_flags, b_flags):
    """Return (table, p_value) for an exact McNemar test on paired flags."""
    # table rows: A correct/wrong. table cols: B correct/wrong.
    cc = 0  # A correct, B correct.
    cw = 0  # A correct, B wrong.
    wc = 0  # A wrong, B correct.
    ww = 0  # A wrong, B wrong.
    for a, b in zip(a_flags, b_flags):
        if a == 1 and b == 1:
            cc += 1
        elif a == 1 and b == 0:
            cw += 1
        elif a == 0 and b == 1:
            wc += 1
        else:
            ww += 1
    b_val = wc  # A wrong, B correct.
    c_val = cw  # A correct, B wrong.
    n = b_val + c_val
    if n == 0:
        p = 1.0
    else:
        k_max = min(b_val, c_val)
        s = 0.0
        for k in range(0, k_max + 1):
            s += math.comb(n, k) * (0.5 ** n)
        p = min(1.0, 2.0 * s)
    return {"cc": cc, "cw": cw, "wc": wc, "ww": ww}, p


def compare(run_a: str, run_b: str):
    """Run the full compare and print the output."""
    resp_a, keys_a = _load_run(run_a)
    resp_b, keys_b = _load_run(run_b)
    ids_a = sorted([r["id"] for r in resp_a])
    ids_b = sorted([r["id"] for r in resp_b])
    if ids_a != ids_b:
        print("ERROR: id sets differ between runs")
        return None
    # Pair by id.
    map_a = {r["id"]: r for r in resp_a}
    map_b = {r["id"]: r for r in resp_b}
    a_flags = [_correct_flag(map_a[i], keys_a) for i in ids_a]
    b_flags = [_correct_flag(map_b[i], keys_b) for i in ids_a]
    diff, lo, hi = paired_bootstrap(a_flags, b_flags)
    table, p = mcnemar_exact(a_flags, b_flags)

    print(f"Run A: {run_a}")
    print(f"Run B: {run_b}")
    print()
    print(f"Accuracy A: {sum(a_flags)/len(a_flags):.4f}")
    print(f"Accuracy B: {sum(b_flags)/len(b_flags):.4f}")
    print(f"Difference (A minus B): {diff:+.4f}")
    print(f"95 percent CI: [{lo:+.4f}, {hi:+.4f}]")
    print()
    print("Paired table (A rows, B cols):")
    print(f"                | B correct | B wrong")
    print(f"  A correct     | {table['cc']:9d} | {table['cw']:7d}")
    print(f"  A wrong       | {table['wc']:9d} | {table['ww']:7d}")
    print()
    print(f"McNemar exact p = {p:.6f}")
    return {
        "run_a": run_a,
        "run_b": run_b,
        "acc_a": sum(a_flags) / len(a_flags),
        "acc_b": sum(b_flags) / len(b_flags),
        "diff": diff,
        "ci_lower": lo,
        "ci_upper": hi,
        "table": table,
        "p_value": p,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("run_a")
    p.add_argument("run_b")
    args = p.parse_args()
    r = compare(args.run_a, args.run_b)
    if r is None:
        sys.exit(1)


if __name__ == "__main__":
    main()
