"""Export the dataset to manual batch files.

Each batch file lists up to 10 patient notes plus the shared instruction.
Review responses go back through import_responses.py.
"""
import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from eval.prompts import build_prompt  # noqa: E402


BATCH_SIZE = 10
PROMPT_VERSION = "p1-batch"


def load_jsonl(path: Path):
    """Return a list of dicts loaded from a JSONL file."""
    out = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def _shared_prompt(condition: str) -> str:
    """Return the shared instruction block with no patient note."""
    full = build_prompt("", condition)
    # Strip the trailing "Patient note:\n" line and anything after.
    marker = "Patient note:"
    idx = full.find(marker)
    if idx != -1:
        full = full[:idx].rstrip()
    return full


def _write_batch(path: Path, instruction: str, items):
    """Write one batch file in the fixed layout."""
    lines = ["[INSTRUCTION]", instruction, "", "[ITEMS]"]
    for it in items:
        lines.append(f"ID: {it['id']}")
        lines.append(it["note"])
        lines.append("")
    lines.append("[RESPONSE FORMAT]")
    lines.append(
        'Respond with a JSON array: '
        '[{"id": "D001", "esi_level": 1, "reason": "one sentence"}, ...]'
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def export(split: str, condition: str):
    """Write batch files for the chosen split and condition."""
    pub = load_jsonl(_HERE / "data" / f"{split}_public.jsonl")
    instruction = _shared_prompt(condition)
    out_root = _HERE / "manual" / f"{split}_{condition}"
    out_root.mkdir(parents=True, exist_ok=True)
    n_batches = (len(pub) + BATCH_SIZE - 1) // BATCH_SIZE
    for b in range(n_batches):
        start = b * BATCH_SIZE
        end = min(start + BATCH_SIZE, len(pub))
        batch_items = pub[start:end]
        path = out_root / f"batch_{b + 1:03d}.txt"
        _write_batch(path, instruction, batch_items)
    print(f"Wrote {n_batches} batches to {out_root}")
    return out_root


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--split", required=True, choices=["dev", "test"])
    p.add_argument("--condition", required=True, choices=["rules", "plain"])
    args = p.parse_args()
    export(args.split, args.condition)


if __name__ == "__main__":
    main()
