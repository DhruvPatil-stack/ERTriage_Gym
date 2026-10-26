"""Import manual batch responses into the standard responses.jsonl form.

The importer scans text for JSON arrays and extracts id, esi_level, reason.
Missing ids get a missing status. Duplicate ids raise a ValueError.
"""
import argparse
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from eval.parse import _coerce_level  # noqa: E402
from eval.metrics import compute_all  # noqa: E402


IMPORT_PROMPT_VERSION = "p1-batch"


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


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


_ARRAY_RE = re.compile(r"\[[^\[\]]*\{.*?\}[^\[\]]*\]", re.DOTALL)


def _find_arrays(text: str):
    """Return a list of parsed JSON arrays found in text."""
    out = []
    # Scan positions of '['. Try to parse the longest valid JSON array from each.
    i = 0
    n = len(text)
    while i < n:
        if text[i] == "[":
            # Walk forward to find a balanced bracket substring.
            depth = 0
            in_str = False
            esc = False
            end = -1
            for j in range(i, n):
                ch = text[j]
                if in_str:
                    if esc:
                        esc = False
                    elif ch == "\\":
                        esc = True
                    elif ch == '"':
                        in_str = False
                else:
                    if ch == '"':
                        in_str = True
                    elif ch == "[":
                        depth += 1
                    elif ch == "]":
                        depth -= 1
                        if depth == 0:
                            end = j
                            break
            if end != -1:
                candidate = text[i:end + 1]
                try:
                    obj = json.loads(candidate)
                    if isinstance(obj, list):
                        out.append(obj)
                except Exception:
                    pass
                i = end + 1
                continue
        i += 1
    return out


def _collect_text(path: Path) -> str:
    """Return the concatenated text of one file or a folder of files."""
    if path.is_dir():
        parts = []
        for p in sorted(path.iterdir()):
            if p.is_file():
                parts.append(p.read_text(encoding="utf-8", errors="replace"))
        return "\n".join(parts)
    return path.read_text(encoding="utf-8", errors="replace")


def import_text(text: str, split: str, condition: str, run_id=None):
    """Parse the text and write responses.jsonl for the run."""
    pub = load_jsonl(_HERE / "data" / f"{split}_public.jsonl")
    all_ids = [r["id"] for r in pub]

    arrays = _find_arrays(text)
    items_by_id = {}
    for arr in arrays:
        for item in arr:
            if not isinstance(item, dict):
                continue
            iid = item.get("id")
            if not isinstance(iid, str):
                continue
            if iid in items_by_id:
                raise ValueError(f"duplicate id in input: {iid}")
            items_by_id[iid] = item

    timestamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    if run_id is None:
        run_id = f"manual_{condition}_{split}_{timestamp}"
    out_dir = _HERE / "runs" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    responses_path = out_dir / "responses.jsonl"

    data_hash = _sha256_file(_HERE / "data" / f"{split}_public.jsonl")

    rows = []
    with responses_path.open("w", encoding="utf-8") as f:
        for pid in all_ids:
            if pid not in items_by_id:
                rec = {
                    "id": pid,
                    "raw": "",
                    "level": None,
                    "reason": None,
                    "status": "missing",
                    "adapter": "manual",
                    "condition": condition,
                    "prompt_version": IMPORT_PROMPT_VERSION,
                    "dataset_hash": data_hash,
                    "latency_s": 0.0,
                    "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                }
            else:
                src = items_by_id[pid]
                level = _coerce_level(src.get("esi_level"))
                reason = src.get("reason")
                if not isinstance(reason, str):
                    reason = None
                if level is None:
                    status = "parse_error"
                elif level < 1 or level > 5:
                    status = "out_of_range"
                else:
                    status = "ok"
                rec = {
                    "id": pid,
                    "raw": json.dumps(src, ensure_ascii=False),
                    "level": level,
                    "reason": reason,
                    "status": status,
                    "adapter": "manual",
                    "condition": condition,
                    "prompt_version": IMPORT_PROMPT_VERSION,
                    "dataset_hash": data_hash,
                    "latency_s": 0.0,
                    "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                }
            rows.append(rec)
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # Compute metrics.
    keys = load_jsonl(_HERE / "data" / f"{split}_key.jsonl")
    keys_dict = {k["id"]: k for k in keys}
    metrics = compute_all(rows, keys_dict)
    results = {
        "run_id": run_id,
        "adapter": "manual",
        "condition": condition,
        "split": split,
        "prompt_version": IMPORT_PROMPT_VERSION,
        "dataset_hash": data_hash,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "metrics": metrics,
    }
    (out_dir / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Import complete. Results in {out_dir}")
    return out_dir


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--split", required=True, choices=["dev", "test"])
    p.add_argument("--condition", required=True, choices=["rules", "plain"])
    p.add_argument("--input", required=True)
    p.add_argument("--run-id", default=None)
    args = p.parse_args()
    text = _collect_text(Path(args.input))
    import_text(text, args.split, args.condition, args.run_id)


if __name__ == "__main__":
    main()
