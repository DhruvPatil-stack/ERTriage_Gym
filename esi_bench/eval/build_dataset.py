"""Build the frozen dev and test splits.

The builder draws 3 patients per variant for dev and 8 per variant for test.
For borderline variants it mixes borderline and non-borderline per the spec.
It stops on 100 collisions and writes to BLOCKED.md.
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

# Make project root importable so generator and config load cleanly.
_HERE = Path(__file__).resolve().parent
_BENCH = _HERE.parent
if str(_BENCH) not in sys.path:
    sys.path.insert(0, str(_BENCH))

from generator import generate_patient  # noqa: E402
from variants import VARIANTS  # noqa: E402
from config import DANGER_HR, DANGER_RR, DANGER_SPO2, SEVERE_PAIN_THRESHOLD  # noqa: E402
from eval.eval_config import DATASET_SEED, BENCHMARK_VERSION  # noqa: E402


BORDERLINE_VARIANTS = [v["variant_id"] for v in VARIANTS if v.get("is_borderline_variant", False)]
ALL_VARIANTS = [v["variant_id"] for v in VARIANTS]


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _draw_variant_items(rng, variant_id: str, borderline: bool, seen: set, limit: int = 100):
    """Draw one unique-note patient for the given variant and borderline flag."""
    for _ in range(limit):
        patient = generate_patient(rng, variant=variant_id, borderline=borderline)
        note = patient["note"]
        if note in seen:
            continue
        seen.add(note)
        return patient
    return None


def _blocked(msg: str) -> None:
    out = _HERE / "reports" / "BLOCKED.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(f"# BLOCKED\n\n{msg}\n", encoding="utf-8")
    print(f"BLOCKED: {msg}")
    sys.exit(1)


def _build_split(rng, per_variant_n: int, borderline_count: int, seen: set):
    """Build one split as a list of patient dicts.

    per_variant_n is the count for each variant.
    borderline_count is the number of borderline patients per borderline variant.
    """
    items = []
    for vid in ALL_VARIANTS:
        is_bl_variant = vid in BORDERLINE_VARIANTS
        if is_bl_variant:
            n_bl = borderline_count
            n_nb = per_variant_n - borderline_count
        else:
            n_bl = 0
            n_nb = per_variant_n
        for _ in range(n_nb):
            p = _draw_variant_items(rng, vid, borderline=False, seen=seen)
            if p is None:
                _blocked(f"could not draw unique non-borderline note for {vid}")
            items.append(p)
        for _ in range(n_bl):
            p = _draw_variant_items(rng, vid, borderline=True, seen=seen)
            if p is None:
                _blocked(f"could not draw unique borderline note for {vid}")
            items.append(p)
    return items


def _assign_ids(items, prefix: str):
    for i, p in enumerate(items, start=1):
        p["id"] = f"{prefix}{i:03d}"
    return items


def _public_record(p):
    return {"id": p["id"], "note": p["note"]}


def _key_record(p):
    return {
        "id": p["id"],
        "variant_id": p["variant_id"],
        "condition_name": p["condition_name"],
        "esi_level": int(p["esi_level"]),
        "acceptable_levels": [int(x) for x in p["acceptable_levels"]],
        "is_borderline": bool(p["is_borderline"]),
        "intended_esi": int(p["typical_esi"]),
    }


def _write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _count_by_variant(items):
    out = {}
    for p in items:
        out[p["variant_id"]] = out.get(p["variant_id"], 0) + 1
    return out


def _count_borderline(items):
    return sum(1 for p in items if p["is_borderline"])


def main():
    rng = np.random.default_rng(DATASET_SEED)
    seen_notes = set()

    dev_items = _build_split(rng, per_variant_n=3, borderline_count=1, seen=seen_notes)
    test_items = _build_split(rng, per_variant_n=8, borderline_count=4, seen=seen_notes)

    # Shuffle each split with the dataset rng, then assign IDs after shuffle.
    dev_perm = rng.permutation(len(dev_items))
    dev_items = [dev_items[i] for i in dev_perm]
    test_perm = rng.permutation(len(test_items))
    test_items = [test_items[i] for i in test_perm]

    dev_items = _assign_ids(dev_items, "D")
    test_items = _assign_ids(test_items, "T")

    data_dir = _HERE / "data"
    dev_pub = data_dir / "dev_public.jsonl"
    dev_key = data_dir / "dev_key.jsonl"
    test_pub = data_dir / "test_public.jsonl"
    test_key = data_dir / "test_key.jsonl"

    _write_jsonl(dev_pub, [_public_record(p) for p in dev_items])
    _write_jsonl(dev_key, [_key_record(p) for p in dev_items])
    _write_jsonl(test_pub, [_public_record(p) for p in test_items])
    _write_jsonl(test_key, [_key_record(p) for p in test_items])

    dev_variants = _count_by_variant(dev_items)
    test_variants = _count_by_variant(test_items)

    source_hashes = {}
    for name in ["config.py", "variants.py", "labeler.py", "generator.py"]:
        p = _BENCH / name
        source_hashes[name] = _sha256_file(p)

    manifest = {
        "benchmark_version": BENCHMARK_VERSION,
        "dataset_seed": DATASET_SEED,
        "splits": {
            "dev": {"total": len(dev_items), "variants": dev_variants},
            "test": {"total": len(test_items), "variants": test_variants},
        },
        "borderline_counts": {
            "dev": _count_borderline(dev_items),
            "test": _count_borderline(test_items),
        },
        "file_hashes": {
            "dev_public.jsonl": _sha256_file(dev_pub),
            "dev_key.jsonl": _sha256_file(dev_key),
            "test_public.jsonl": _sha256_file(test_pub),
            "test_key.jsonl": _sha256_file(test_key),
        },
        "source_hashes": source_hashes,
        "thresholds": {
            "DANGER_HR": DANGER_HR,
            "DANGER_RR": DANGER_RR,
            "DANGER_SPO2": DANGER_SPO2,
            "SEVERE_PAIN_THRESHOLD": SEVERE_PAIN_THRESHOLD,
        },
    }
    (data_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    # Report.
    print("variant_id | dev_count | test_count")
    print("-----------+-----------+-----------")
    for vid in ALL_VARIANTS:
        print(f"{vid:10s} | {dev_variants.get(vid,0):9d} | {test_variants.get(vid,0):10d}")
    print()
    print(f"Dev total: {len(dev_items)}  Test total: {len(test_items)}")
    print(f"Borderline dev: {_count_borderline(dev_items)}  Borderline test: {_count_borderline(test_items)}")
    print()
    print("Sample dev public records:")
    for p in dev_items[:3]:
        print(json.dumps(_public_record(p), ensure_ascii=False))


if __name__ == "__main__":
    main()
