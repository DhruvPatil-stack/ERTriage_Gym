"""Run one adapter over one split and record responses.

The runner skips items that already appear in responses.jsonl.
Each record goes to disk one at a time.
"""
import argparse
import datetime
import hashlib
import json
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from eval.eval_config import PROMPT_VERSION  # noqa: E402
from eval.parse import parse_response  # noqa: E402
from eval.prompts import build_prompt  # noqa: E402
from eval.metrics import compute_all  # noqa: E402
from eval.adapters import MOCK_NAMES, build_mock_adapter  # noqa: E402


def sha256_file(path: Path) -> str:
    """Return the SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def check_manifest_hash(split: str) -> bool:
    """Return True if the public file hash matches the manifest."""
    manifest = json.loads((_HERE / "data" / "manifest.json").read_text(encoding="utf-8"))
    name = f"{split}_public.jsonl"
    expected = manifest["file_hashes"][name]
    actual = sha256_file(_HERE / "data" / name)
    return expected == actual


def load_jsonl(path: Path):
    """Return a list of dicts loaded from a JSONL file."""
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _load_split(split):
    """Return public rows, key records, and the note map for a split."""
    pub = load_jsonl(_HERE / "data" / f"{split}_public.jsonl")
    keys = load_jsonl(_HERE / "data" / f"{split}_key.jsonl")
    note_map = {r["id"]: r["note"] for r in pub}
    return pub, keys, note_map


def _append_test_access(adapter, condition, prompt_version, run_id):
    """Add a line to the test access log. Warn on repeat use."""
    path = _HERE / "runs" / "test_access_log.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    # Warn if the same adapter and prompt_version were used before.
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                if row.get("adapter") == adapter and row.get("prompt_version") == prompt_version:
                    print(f"WARN: adapter {adapter} with prompt {prompt_version} already ran on test")
    rec = {
        "adapter": adapter,
        "condition": condition,
        "prompt_version": prompt_version,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "run_id": run_id,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


def _resolve_adapter(adapter_name, dev_keys, dev_note_map, split_keys, split_note_map):
    """Return an adapter instance for the given name."""
    if adapter_name in MOCK_NAMES:
        return build_mock_adapter(
            adapter_name,
            dev_key_records=dev_keys,
            dev_note_map=dev_note_map,
            split_key_records=split_keys,
            split_note_map=split_note_map,
        )
    # Fall through to Ollama for real tags.
    try:
        from eval.adapters_ollama import OllamaAdapter
    except Exception as e:
        raise RuntimeError(f"cannot import OllamaAdapter: {e}")
    return OllamaAdapter(adapter_name)


def run(split, condition, adapter_name, allow_test=False, run_id=None):
    """Run an adapter on a split and write the records plus the metrics."""
    if condition not in ("rules", "plain"):
        print(f"ERROR: unknown condition {condition}")
        return 2

    # Hash check.
    if not check_manifest_hash(split):
        print("ERROR: data file hash does not match the manifest")
        return 2

    if split == "test" and not allow_test:
        print("ERROR: test split needs --allow-test")
        return 2

    timestamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    if run_id is None:
        safe_name = adapter_name.replace(":", "-").replace("/", "-")
        run_id = f"{safe_name}_{condition}_{split}_{timestamp}"

    if split == "test":
        _append_test_access(adapter_name, condition, PROMPT_VERSION, run_id)

    out_dir = _HERE / "runs" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    responses_path = out_dir / "responses.jsonl"

    # Load existing responses if present.
    completed = set()
    if responses_path.exists():
        for row in load_jsonl(responses_path):
            completed.add(row["id"])
        print(f"Found {len(completed)} completed items. Resuming.")

    pub, split_keys, split_note_map = _load_split(split)

    # Dev keys and notes needed for ConditionBestAdapter.
    if split == "dev":
        dev_pub = pub
        dev_keys = split_keys
        dev_note_map = split_note_map
    else:
        dev_pub = load_jsonl(_HERE / "data" / "dev_public.jsonl")
        dev_keys = load_jsonl(_HERE / "data" / "dev_key.jsonl")
        dev_note_map = {r["id"]: r["note"] for r in dev_pub}

    adapter = _resolve_adapter(adapter_name, dev_keys, dev_note_map, split_keys, split_note_map)

    data_hash = sha256_file(_HERE / "data" / f"{split}_public.jsonl")
    total = len(pub)
    done = len(completed)

    with responses_path.open("a", encoding="utf-8") as f:
        for i, row in enumerate(pub):
            if row["id"] in completed:
                continue
            note = row["note"]
            prompt = build_prompt(note, condition)
            t0 = time.time()
            try:
                raw = adapter.ask(prompt)
                status_from_adapter = "ok"
            except Exception as e:
                raw = ""
                status_from_adapter = "adapter_error"
            latency = time.time() - t0
            if status_from_adapter == "adapter_error" or raw == "" or raw is None:
                parsed = {"level": None, "reason": None, "status": "adapter_error"}
            else:
                parsed = parse_response(raw)
            rec = {
                "id": row["id"],
                "raw": raw,
                "level": parsed["level"],
                "reason": parsed["reason"],
                "status": parsed["status"],
                "adapter": adapter_name,
                "condition": condition,
                "prompt_version": PROMPT_VERSION,
                "dataset_hash": data_hash,
                "latency_s": latency,
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            done += 1
            if done % 25 == 0 or done == total:
                print(f"Progress: {done}/{total} items done")

    # Compute metrics.
    all_rows = load_jsonl(responses_path)
    keys_dict = {k["id"]: k for k in split_keys}
    metrics = compute_all(all_rows, keys_dict)
    results = {
        "run_id": run_id,
        "adapter": adapter_name,
        "condition": condition,
        "split": split,
        "prompt_version": PROMPT_VERSION,
        "dataset_hash": data_hash,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "metrics": metrics,
    }
    (out_dir / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Run complete. Results in {out_dir}")
    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--split", required=True, choices=["dev", "test"])
    p.add_argument("--condition", required=True, choices=["rules", "plain"])
    p.add_argument("--adapter", required=True)
    p.add_argument("--allow-test", action="store_true")
    p.add_argument("--run-id", default=None)
    args = p.parse_args()
    code = run(args.split, args.condition, args.adapter, args.allow_test, args.run_id)
    sys.exit(code)


if __name__ == "__main__":
    main()
