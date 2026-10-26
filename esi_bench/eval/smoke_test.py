"""Smoke test: run SMOKE_N dev items per model and record latency.

The script tracks parse errors. If above PARSE_ERROR_LIMIT it tries prompt p2.
Report goes to eval/reports/smoke_test.txt.
"""
import json
import re
import sys
import time
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from eval.eval_config import SMOKE_N, PARSE_ERROR_LIMIT  # noqa: E402
from eval.parse import parse_response  # noqa: E402
from eval.prompts import build_prompt  # noqa: E402
from eval.adapters_ollama import OllamaAdapter  # noqa: E402


def load_jsonl(path):
    """Load one JSONL file into a list of dicts."""
    out = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def _parse_models_txt():
    """Return the list of installed model tags from models.txt."""
    path = _HERE / "reports" / "models.txt"
    if not path.exists():
        return []
    tags = []
    in_section = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("Installed model digests"):
            in_section = True
            continue
        if in_section:
            parts = line.split()
            if len(parts) >= 2:
                tags.append(parts[0])
    # Filter to our planned 3 if present.
    planned = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("planned_models:"):
            planned = [x.strip() for x in line.split(":", 1)[1].split(",")]
    if planned:
        tags = [t for t in planned if t in tags]
    return tags


def _augment_prompt_p2(prompt):
    """Add a stricter instruction tail to improve JSON output."""
    return prompt + "\n\nRespond with ONLY a JSON object, nothing else."


def _smoke_one(model_tag, items, condition, prompt_tail=""):
    """Run one model over the items. Return (parse_errs, latencies, levels)."""
    adapter = OllamaAdapter(model_tag)
    latencies = []
    parse_errs = 0
    results = []
    for i, item in enumerate(items):
        prompt = build_prompt(item["note"], condition)
        if prompt_tail:
            prompt = prompt + prompt_tail
        t0 = time.time()
        raw = adapter.ask(prompt)
        dt = time.time() - t0
        parsed = parse_response(raw)
        if i > 0:
            latencies.append(dt)
        if parsed["status"] != "ok":
            parse_errs += 1
        results.append({"id": item["id"], "status": parsed["status"], "latency": dt, "raw": raw[:200]})
    return parse_errs, latencies, results


def main():
    pub = load_jsonl(_HERE / "data" / "dev_public.jsonl")
    items = pub[:SMOKE_N]

    tags = _parse_models_txt()
    if not tags:
        print("No model tags from models.txt. Nothing to smoke.")
        return 1

    out_lines = [
        "ESI smoke test report",
        "---------------------",
        f"n_items: {SMOKE_N} (discard first for warm-up)",
        f"condition: rules",
        "",
    ]
    out_lines.append(
        f"{'model':<20} | {'median_s':>8} | {'mean_s':>7} | {'parse_err':>9} | {'prompt':<4}"
    )
    out_lines.append("-" * 70)

    smoke_results = {}
    for tag in tags:
        print(f"Smoke: {tag}")
        parse_errs, lats, _ = _smoke_one(tag, items, "rules")
        n_tested = len(items) - 1
        err_rate = parse_errs / len(items)
        tail = ""
        prompt_tag = "p1"
        if err_rate > PARSE_ERROR_LIMIT:
            print(f"  parse errors {parse_errs}/{len(items)} over limit. Retry with p2.")
            tail = "\n\nRespond with ONLY a JSON object, nothing else."
            parse_errs, lats, _ = _smoke_one(tag, items, "rules", prompt_tail=tail)
            prompt_tag = "p2"
        median_s = float(np.median(lats)) if lats else 0.0
        mean_s = float(np.mean(lats)) if lats else 0.0
        smoke_results[tag] = {"median_s": median_s, "mean_s": mean_s, "parse_errs": parse_errs, "prompt": prompt_tag}
        out_lines.append(
            f"{tag:<20} | {median_s:>8.2f} | {mean_s:>7.2f} | {parse_errs:>9} | {prompt_tag:<4}"
        )

    out_path = _HERE / "reports" / "smoke_test.txt"
    out_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    print("\n".join(out_lines))
    print(f"Wrote {out_path}")

    # Save a JSON copy for the run plan.
    (_HERE / "reports" / "smoke_results.json").write_text(
        json.dumps(smoke_results, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
