"""Write review CSV files for a single run.

One file lists every wrong or non-ok item. The other lists per-variant accuracy.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


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


def build_sheets(run_id: str):
    """Build the two CSV files for the given run."""
    rdir = _HERE / "runs" / run_id
    responses = load_jsonl(rdir / "responses.jsonl")
    results = json.loads((rdir / "results.json").read_text(encoding="utf-8"))
    split = results["split"]
    public = load_jsonl(_HERE / "data" / f"{split}_public.jsonl")
    keys = load_jsonl(_HERE / "data" / f"{split}_key.jsonl")
    note_map = {r["id"]: r["note"] for r in public}
    key_map = {k["id"]: k for k in keys}

    wrong_rows = []
    variant_stats = {}
    for r in responses:
        rid = r["id"]
        k = key_map[rid]
        vid = k["variant_id"]
        cond_name = k["condition_name"]
        if vid not in variant_stats:
            variant_stats[vid] = {"condition_name": cond_name, "n": 0, "n_correct": 0}
        variant_stats[vid]["n"] += 1
        accept = [int(x) for x in k["acceptable_levels"]]
        is_ok = r.get("status") == "ok" and r.get("level") is not None
        is_corr = is_ok and int(r["level"]) in accept
        if is_corr:
            variant_stats[vid]["n_correct"] += 1
        if (not is_ok) or (not is_corr):
            wrong_rows.append({
                "id": rid,
                "variant_id": vid,
                "note": note_map[rid],
                "esi_level": k["esi_level"],
                "acceptable_levels": "|".join(str(x) for x in accept),
                "answer": r.get("level"),
                "model_reason": r.get("reason") or "",
                "verdict": "",
                "handbook_ref": "",
                "comment": "",
            })

    wrong_rows.sort(key=lambda row: (row["variant_id"], row["id"]))
    out_wrong = rdir / "review_wrong.csv"
    with out_wrong.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "id", "variant_id", "note", "esi_level", "acceptable_levels",
            "answer", "model_reason", "verdict", "handbook_ref", "comment",
        ])
        w.writeheader()
        for row in wrong_rows:
            w.writerow(row)

    out_var = rdir / "review_variant_accuracy.csv"
    with out_var.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["variant_id", "condition_name", "n_items", "n_correct", "accuracy"])
        for vid in sorted(variant_stats.keys()):
            s = variant_stats[vid]
            acc = s["n_correct"] / s["n"] if s["n"] else 0.0
            w.writerow([vid, s["condition_name"], s["n"], s["n_correct"], f"{acc:.4f}"])

    print(f"Wrote {out_wrong}")
    print(f"Wrote {out_var}")
    return out_wrong, out_var


def main():
    p = argparse.ArgumentParser()
    p.add_argument("run_id")
    args = p.parse_args()
    build_sheets(args.run_id)


if __name__ == "__main__":
    main()
