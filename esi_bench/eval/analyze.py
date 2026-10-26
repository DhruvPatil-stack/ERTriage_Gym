"""Suspect key analysis across test runs.

An item is suspect if a strong majority of models agree on a wrong answer.
A variant is suspect if half of its items are suspect with the same answer.
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from eval.eval_config import CONSENSUS_SHARE  # noqa: E402


def load_jsonl(path):
    """Return a list of dicts from a JSONL file."""
    out = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def _collect_test_runs():
    """Return a list of (run_id, responses, meta) for every test run."""
    runs_dir = _HERE / "runs"
    out = []
    if not runs_dir.exists():
        return out
    for rd in sorted(runs_dir.iterdir()):
        if not rd.is_dir():
            continue
        resp = rd / "responses.jsonl"
        meta = rd / "results.json"
        if not resp.exists() or not meta.exists():
            continue
        try:
            m = json.loads(meta.read_text(encoding="utf-8"))
        except Exception:
            continue
        if m.get("split") != "test":
            continue
        out.append((rd.name, load_jsonl(resp), m))
    return out


def main():
    key = {k["id"]: k for k in load_jsonl(_HERE / "data" / "test_key.jsonl")}
    pub = {r["id"]: r for r in load_jsonl(_HERE / "data" / "test_public.jsonl")}
    runs = _collect_test_runs()
    if not runs:
        print("No test runs found. Nothing to analyze.")
        return 0

    # Collect answers per id.
    answers = defaultdict(list)
    for rid, resp, _ in runs:
        for r in resp:
            if r.get("status") == "ok" and r.get("level") is not None:
                answers[r["id"]].append(int(r["level"]))

    suspect_items = []
    for iid, levels in answers.items():
        if iid not in key:
            continue
        n = len(levels)
        if n == 0:
            continue
        cnt = Counter(levels)
        best_level, best_count = cnt.most_common(1)[0]
        share = best_count / n
        accept = [int(x) for x in key[iid]["acceptable_levels"]]
        if share >= CONSENSUS_SHARE and best_level not in accept:
            suspect_items.append({
                "id": iid,
                "variant_id": key[iid]["variant_id"],
                "condition_name": key[iid]["condition_name"],
                "key_level": int(key[iid]["esi_level"]),
                "consensus": best_level,
                "share": share,
                "note": pub[iid]["note"],
            })

    # Group by variant.
    per_variant = defaultdict(list)
    for s in suspect_items:
        per_variant[s["variant_id"]].append(s)

    # Variant is suspect if at least half its items are suspect with same answer.
    variant_rows = []
    for vid, items in per_variant.items():
        total_v = sum(1 for i in answers if key.get(i, {}).get("variant_id") == vid)
        answer_counts = Counter(s["consensus"] for s in items)
        for consensus_ans, n in answer_counts.most_common():
            if total_v > 0 and n >= total_v / 2.0:
                variant_rows.append({
                    "variant_id": vid,
                    "condition_name": items[0]["condition_name"],
                    "n_items": total_v,
                    "n_suspect": n,
                    "consensus_answer": consensus_ans,
                    "key_level": items[0]["key_level"],
                })

    out = _HERE / "reports" / "suspect_keys.csv"
    with out.open("w", encoding="utf-8") as f:
        f.write("variant_id,condition_name,n_items,n_suspect,consensus_answer,key_level\n")
        for r in variant_rows:
            f.write(
                f"{r['variant_id']},{r['condition_name']},{r['n_items']},"
                f"{r['n_suspect']},{r['consensus_answer']},{r['key_level']}\n"
            )

    print(f"Wrote {out}")
    print(f"Suspect variants: {len(variant_rows)}")
    print()
    print("Top 20 suspect items:")
    suspect_items.sort(key=lambda s: -s["share"])
    for s in suspect_items[:20]:
        print(f"  {s['id']} v={s['variant_id']} key={s['key_level']} ans={s['consensus']} share={s['share']:.2f}")
        print(f"    {s['note'][:100]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
