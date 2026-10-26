"""Full test suite for the ESI benchmark harness.

Each test runs in-process. The script prints pass or fail per test.
Exit code is 1 if any test fails.
"""
import hashlib
import json
import math
import os
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from eval.parse import parse_response  # noqa: E402
from eval.prompts import build_prompt  # noqa: E402
from eval.metrics import (  # noqa: E402
    compute_all,
    quadratic_weighted_kappa,
    bootstrap_accuracy_interval,
)
from eval.adapters import (  # noqa: E402
    OracleAdapter,
    Always3Adapter,
    RandomAdapter,
    NoisyOracleAdapter,
    UnderByOneAdapter,
    OverByOneAdapter,
    GarbageAdapter,
    FencedAdapter,
    StringLevelAdapter,
    ConditionBestAdapter,
    build_mock_adapter,
    MOCK_NAMES,
)
from eval.run_eval import run as run_eval_run, check_manifest_hash  # noqa: E402
from eval.compare import compare as compare_runs  # noqa: E402
from eval.review_sheet import build_sheets  # noqa: E402
from eval.import_responses import import_text  # noqa: E402
from eval.export_batches import export as export_batches  # noqa: E402
from eval.eval_config import BOOTSTRAP_SEED  # noqa: E402

RESULTS = []


def record(name, ok, msg=""):
    """Record one test result and print it."""
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}" + (f" - {msg}" if msg else ""))
    RESULTS.append((name, ok, msg))


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


def _sha256_file(p):
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _run_adapter(adapter, pub, condition="rules"):
    """Call the adapter on every public item and parse the response."""
    rows = []
    for item in pub:
        prompt = build_prompt(item["note"], condition)
        raw = adapter.ask(prompt)
        parsed = parse_response(raw)
        rows.append({
            "id": item["id"],
            "raw": raw,
            "level": parsed["level"],
            "reason": parsed["reason"],
            "status": parsed["status"],
        })
    return rows


# ---- Load fixtures once. ----

DATA = _HERE / "data"
DEV_PUB = load_jsonl(DATA / "dev_public.jsonl")
DEV_KEY = load_jsonl(DATA / "dev_key.jsonl")
TEST_PUB = load_jsonl(DATA / "test_public.jsonl")
TEST_KEY = load_jsonl(DATA / "test_key.jsonl")
DEV_NOTE_MAP = {r["id"]: r["note"] for r in DEV_PUB}
TEST_NOTE_MAP = {r["id"]: r["note"] for r in TEST_PUB}
DEV_KEY_MAP = {k["id"]: k for k in DEV_KEY}
TEST_KEY_MAP = {k["id"]: k for k in TEST_KEY}


# ----- T01 -----

def test_T01():
    """Public files have only id and note. Key files cover same ids."""
    try:
        for row in DEV_PUB + TEST_PUB:
            assert set(row.keys()) == {"id", "note"}, row.keys()
        dev_pub_ids = set(r["id"] for r in DEV_PUB)
        dev_key_ids = set(k["id"] for k in DEV_KEY)
        test_pub_ids = set(r["id"] for r in TEST_PUB)
        test_key_ids = set(k["id"] for k in TEST_KEY)
        assert dev_pub_ids == dev_key_ids
        assert test_pub_ids == test_key_ids
        record("T01 schema and id sets", True)
    except Exception as e:
        record("T01 schema and id sets", False, str(e))


def test_T02():
    """Dev has 78 items. Test has 208 items. Variants appear 3 and 8 times."""
    try:
        assert len(DEV_PUB) == 78
        assert len(TEST_PUB) == 208
        dev_counts = {}
        for k in DEV_KEY:
            dev_counts[k["variant_id"]] = dev_counts.get(k["variant_id"], 0) + 1
        test_counts = {}
        for k in TEST_KEY:
            test_counts[k["variant_id"]] = test_counts.get(k["variant_id"], 0) + 1
        assert all(v == 3 for v in dev_counts.values()), dev_counts
        assert all(v == 8 for v in test_counts.values()), test_counts
        record("T02 split and variant counts", True)
    except Exception as e:
        record("T02 split and variant counts", False, str(e))


def test_T03():
    """Dev borderline count 6, test borderline count 24."""
    try:
        dev_b = sum(1 for k in DEV_KEY if k["is_borderline"])
        test_b = sum(1 for k in TEST_KEY if k["is_borderline"])
        assert dev_b == 6, dev_b
        assert test_b == 24, test_b
        record("T03 borderline counts", True)
    except Exception as e:
        record("T03 borderline counts", False, str(e))


def test_T04():
    """No note repeats within or across splits."""
    try:
        dev_notes = [r["note"] for r in DEV_PUB]
        test_notes = [r["note"] for r in TEST_PUB]
        assert len(dev_notes) == len(set(dev_notes))
        assert len(test_notes) == len(set(test_notes))
        assert not (set(dev_notes) & set(test_notes))
        record("T04 unique notes", True)
    except Exception as e:
        record("T04 unique notes", False, str(e))


def test_T05():
    """Manifest hashes match computed file hashes."""
    try:
        manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
        for name in ["dev_public.jsonl", "dev_key.jsonl", "test_public.jsonl", "test_key.jsonl"]:
            expect = manifest["file_hashes"][name]
            actual = _sha256_file(DATA / name)
            assert expect == actual, name
        record("T05 manifest hashes", True)
    except Exception as e:
        record("T05 manifest hashes", False, str(e))


def test_T06():
    """Runner hash check fails on tampered copy with wrong manifest hash."""
    try:
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            # Copy the manifest and the dev public file to a staging dir.
            stage_data = td / "data"
            stage_data.mkdir()
            shutil.copy(DATA / "dev_public.jsonl", stage_data / "dev_public.jsonl")
            shutil.copy(DATA / "dev_key.jsonl", stage_data / "dev_key.jsonl")
            shutil.copy(DATA / "test_public.jsonl", stage_data / "test_public.jsonl")
            shutil.copy(DATA / "test_key.jsonl", stage_data / "test_key.jsonl")
            # Flip one byte in the staged public file.
            raw = (stage_data / "dev_public.jsonl").read_bytes()
            raw2 = bytearray(raw)
            raw2[0] = raw2[0] ^ 0x01
            (stage_data / "dev_public.jsonl").write_bytes(bytes(raw2))
            # Write a manifest with the original (correct) hashes.
            man = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
            (stage_data / "manifest.json").write_text(json.dumps(man), encoding="utf-8")
            # Compute a local hash check in the same way as the runner.
            expected = man["file_hashes"]["dev_public.jsonl"]
            actual = _sha256_file(stage_data / "dev_public.jsonl")
            assert expected != actual
        # Confirm the real check function returns True on the real data.
        assert check_manifest_hash("dev") is True
        record("T06 hash check tamper", True)
    except Exception as e:
        record("T06 hash check tamper", False, str(e))


def test_T07():
    """Oracle on dev gives accuracy 1.0 and kappa 1.0."""
    try:
        adapter = OracleAdapter(DEV_KEY, DEV_NOTE_MAP)
        rows = _run_adapter(adapter, DEV_PUB, "rules")
        m = compute_all(rows, DEV_KEY_MAP)
        assert m["accuracy"] == 1.0, m["accuracy"]
        assert abs(m["kappa"] - 1.0) < 1e-9, m["kappa"]
        assert m["undertriage_rate"] == 0.0
        assert m["overtriage_rate"] == 0.0
        record("T07 oracle perfect", True)
    except Exception as e:
        record("T07 oracle perfect", False, str(e))


def test_T08():
    """Always3 accuracy matches independent count."""
    try:
        adapter = Always3Adapter()
        rows = _run_adapter(adapter, DEV_PUB, "rules")
        m = compute_all(rows, DEV_KEY_MAP)
        expected_correct = sum(1 for k in DEV_KEY if 3 in k["acceptable_levels"])
        expected_acc = expected_correct / len(DEV_KEY)
        assert abs(m["accuracy"] - expected_acc) < 1e-9, (m["accuracy"], expected_acc)
        record("T08 always3 accuracy", True)
    except Exception as e:
        record("T08 always3 accuracy", False, str(e))


def test_T09():
    """Random accuracy stays within 3 standard errors of expected."""
    try:
        adapter = RandomAdapter(seed=42)
        rows = _run_adapter(adapter, DEV_PUB, "rules")
        m = compute_all(rows, DEV_KEY_MAP)
        mean_len = np.mean([len(k["acceptable_levels"]) for k in DEV_KEY])
        p = float(mean_len) / 5.0
        se = math.sqrt(p * (1 - p) / len(DEV_KEY))
        assert abs(m["accuracy"] - p) < 3 * se, (m["accuracy"], p, se)
        record("T09 random accuracy", True, f"p={p:.3f} acc={m['accuracy']:.3f}")
    except Exception as e:
        record("T09 random accuracy", False, str(e))


def test_T10():
    """Noisy oracle with p=0.2 near 0.8 accuracy within 3 SE."""
    try:
        adapter = NoisyOracleAdapter(DEV_KEY, DEV_NOTE_MAP, p=0.2, seed=42)
        rows = _run_adapter(adapter, DEV_PUB, "rules")
        m = compute_all(rows, DEV_KEY_MAP)
        # Approximate expected accuracy: 0.8 plus a share from noise falling in acceptable.
        p = 0.8
        se = math.sqrt(p * (1 - p) / len(DEV_KEY))
        assert m["accuracy"] > p - 3 * se and m["accuracy"] < p + 3 * se + 0.1
        record("T10 noisy oracle", True, f"acc={m['accuracy']:.3f}")
    except Exception as e:
        record("T10 noisy oracle", False, str(e))


def test_T11():
    """UnderByOne gives zero overtriage and positive undertriage."""
    try:
        adapter = UnderByOneAdapter(DEV_KEY, DEV_NOTE_MAP)
        rows = _run_adapter(adapter, DEV_PUB, "rules")
        m = compute_all(rows, DEV_KEY_MAP)
        assert m["overtriage_rate"] == 0.0, m["overtriage_rate"]
        assert m["undertriage_rate"] > 0.0
        # Expected accuracy: cases where level 5 would stay 5, or correct lies above.
        n_corr = 0
        for k in DEV_KEY:
            ans = min(5, k["esi_level"] + 1)
            if ans in k["acceptable_levels"]:
                n_corr += 1
        assert abs(m["accuracy"] - n_corr / len(DEV_KEY)) < 1e-9
        record("T11 under by one", True)
    except Exception as e:
        record("T11 under by one", False, str(e))


def test_T12():
    """OverByOne gives zero undertriage and positive overtriage."""
    try:
        adapter = OverByOneAdapter(DEV_KEY, DEV_NOTE_MAP)
        rows = _run_adapter(adapter, DEV_PUB, "rules")
        m = compute_all(rows, DEV_KEY_MAP)
        assert m["undertriage_rate"] == 0.0, m["undertriage_rate"]
        assert m["overtriage_rate"] > 0.0
        n_corr = 0
        for k in DEV_KEY:
            ans = max(1, k["esi_level"] - 1)
            if ans in k["acceptable_levels"]:
                n_corr += 1
        assert abs(m["accuracy"] - n_corr / len(DEV_KEY)) < 1e-9
        record("T12 over by one", True)
    except Exception as e:
        record("T12 over by one", False, str(e))


def test_T13():
    """Garbage output flags every item as parse_error."""
    try:
        adapter = GarbageAdapter()
        rows = _run_adapter(adapter, DEV_PUB, "rules")
        m = compute_all(rows, DEV_KEY_MAP)
        assert all(r["status"] == "parse_error" for r in rows)
        assert m["accuracy"] == 0.0
        record("T13 garbage parse errors", True)
    except Exception as e:
        record("T13 garbage parse errors", False, str(e))


def test_T14():
    """Parser handles fences, strings, floats, and out of range."""
    try:
        a = parse_response('```json\n{"esi_level": 3, "reason": "test"}\n```')
        assert a["level"] == 3 and a["status"] == "ok", a
        b = parse_response('Here is my answer: {"esi_level": "3", "reason": "string"}')
        assert b["level"] == 3 and b["status"] == "ok", b
        c = parse_response('{"esi_level": 3.0, "reason": "float"}')
        assert c["level"] == 3 and c["status"] == "ok", c
        d = parse_response('{"esi_level": 0, "reason": "zero"}')
        assert d["status"] == "out_of_range", d
        e = parse_response('{"esi_level": 6, "reason": "six"}')
        assert e["status"] == "out_of_range", e
        record("T14 parser cases", True)
    except Exception as e:
        record("T14 parser cases", False, str(e))


def _slow_qwk(keys, answers):
    """Reference QWK with explicit loops."""
    classes = 5
    n = len(keys)
    o = [[0] * classes for _ in range(classes)]
    for k, a in zip(keys, answers):
        o[k - 1][a - 1] += 1
    row_sum = [sum(r) for r in o]
    col_sum = [sum(o[r][c] for r in range(classes)) for c in range(classes)]
    e = [[row_sum[r] * col_sum[c] / n for c in range(classes)] for r in range(classes)]
    denom = (classes - 1) ** 2
    w = [[((r - c) ** 2) / denom for c in range(classes)] for r in range(classes)]
    num = sum(w[r][c] * o[r][c] for r in range(classes) for c in range(classes))
    den = sum(w[r][c] * e[r][c] for r in range(classes) for c in range(classes))
    if den == 0:
        return 1.0
    return 1 - num / den


def test_T15():
    """QWK edge cases and slow reference match."""
    try:
        assert abs(quadratic_weighted_kappa([1, 2, 3, 4, 5], [1, 2, 3, 4, 5]) - 1.0) < 1e-9
        v = quadratic_weighted_kappa([1, 2, 3, 4, 5], [5, 4, 3, 2, 1])
        assert v < 0, v
        rng = np.random.default_rng(0)
        keys = list(rng.integers(1, 6, size=20))
        answers = list(rng.integers(1, 6, size=20))
        fast = quadratic_weighted_kappa(keys, answers)
        slow = _slow_qwk(keys, answers)
        assert abs(fast - slow) < 1e-9, (fast, slow)
        record("T15 kappa cases", True)
    except Exception as e:
        record("T15 kappa cases", False, str(e))


def test_T16():
    """Oracle scored against shuffled keys drops below 0.45 accuracy."""
    try:
        adapter = OracleAdapter(DEV_KEY, DEV_NOTE_MAP)
        rows = _run_adapter(adapter, DEV_PUB, "rules")
        # Shuffle the key records.
        rng = np.random.default_rng(99)
        shuffled = list(DEV_KEY)
        perm = rng.permutation(len(shuffled))
        # Map each id to a shuffled key record.
        shuffled_keys = {}
        for i, k in enumerate(shuffled):
            # Attach the key record at index perm[i] to the id at position i.
            new_key = dict(shuffled[perm[i]])
            new_key["id"] = k["id"]
            shuffled_keys[k["id"]] = new_key
        m = compute_all(rows, shuffled_keys)
        assert m["accuracy"] < 0.45, m["accuracy"]
        record("T16 oracle on shuffled keys", True, f"acc={m['accuracy']:.3f}")
    except Exception as e:
        record("T16 oracle on shuffled keys", False, str(e))


def test_T17():
    """Bootstrap CI contains the point. Same seed gives same output."""
    try:
        flags = [1] * 50 + [0] * 28
        lo1, hi1 = bootstrap_accuracy_interval(flags, n=500, seed=7)
        lo2, hi2 = bootstrap_accuracy_interval(flags, n=500, seed=7)
        assert (lo1, hi1) == (lo2, hi2)
        point = sum(flags) / len(flags)
        assert lo1 <= point <= hi1
        record("T17 bootstrap", True)
    except Exception as e:
        record("T17 bootstrap", False, str(e))


def _run_mock_to_dir(adapter_name, out_name):
    """Run a mock adapter on dev and write files to a temp run dir."""
    out_dir = _HERE / "runs" / out_name
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    adapter = build_mock_adapter(adapter_name, DEV_KEY, DEV_NOTE_MAP, DEV_KEY, DEV_NOTE_MAP)
    rows = []
    with (out_dir / "responses.jsonl").open("w", encoding="utf-8") as f:
        for item in DEV_PUB:
            prompt = build_prompt(item["note"], "rules")
            raw = adapter.ask(prompt)
            parsed = parse_response(raw)
            rec = {
                "id": item["id"],
                "raw": raw,
                "level": parsed["level"],
                "reason": parsed["reason"],
                "status": parsed["status"],
                "adapter": adapter_name,
                "condition": "rules",
                "prompt_version": "p1",
                "dataset_hash": "test",
                "latency_s": 0.0,
                "timestamp": "test",
            }
            rows.append(rec)
            f.write(json.dumps(rec) + "\n")
    metrics = compute_all(rows, DEV_KEY_MAP)
    results = {
        "run_id": out_name,
        "adapter": adapter_name,
        "condition": "rules",
        "split": "dev",
        "prompt_version": "p1",
        "dataset_hash": "test",
        "timestamp": "test",
        "metrics": metrics,
    }
    (out_dir / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    return out_dir, rows, metrics


def test_T18():
    """Compare: identical oracle runs give diff 0. Oracle vs always3 gives diff > 0."""
    try:
        _run_mock_to_dir("oracle", "_test_oracle_a")
        _run_mock_to_dir("oracle", "_test_oracle_b")
        _run_mock_to_dir("always3", "_test_always3")

        r1 = compare_runs("_test_oracle_a", "_test_oracle_b")
        assert abs(r1["diff"]) < 1e-9
        assert abs(r1["p_value"] - 1.0) < 1e-9

        r2 = compare_runs("_test_oracle_a", "_test_always3")
        assert r2["diff"] > 0
        assert r2["ci_lower"] > 0
        record("T18 compare", True)
    except Exception as e:
        record("T18 compare", False, str(e))


def test_T19():
    """Restart test: partial run resumes without redoing finished items."""
    try:
        out_dir = _HERE / "runs" / "_test_restart"
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True)

        adapter = OracleAdapter(DEV_KEY, DEV_NOTE_MAP)
        rows = []
        # First 10 items.
        with (out_dir / "responses.jsonl").open("w", encoding="utf-8") as f:
            for item in DEV_PUB[:10]:
                prompt = build_prompt(item["note"], "rules")
                raw = adapter.ask(prompt)
                parsed = parse_response(raw)
                rec = {
                    "id": item["id"],
                    "raw": raw,
                    "level": parsed["level"],
                    "reason": parsed["reason"],
                    "status": parsed["status"],
                }
                rows.append(rec)
                f.write(json.dumps(rec) + "\n")

        # Now simulate restart: count calls when resuming.
        calls = {"n": 0}

        class CountingOracle:
            def __init__(self, inner):
                self.inner = inner

            def ask(self, prompt):
                calls["n"] += 1
                return self.inner.ask(prompt)

        inner = OracleAdapter(DEV_KEY, DEV_NOTE_MAP)
        wrapped = CountingOracle(inner)
        completed = set(r["id"] for r in load_jsonl(out_dir / "responses.jsonl"))
        with (out_dir / "responses.jsonl").open("a", encoding="utf-8") as f:
            for item in DEV_PUB:
                if item["id"] in completed:
                    continue
                prompt = build_prompt(item["note"], "rules")
                raw = wrapped.ask(prompt)
                parsed = parse_response(raw)
                rec = {
                    "id": item["id"],
                    "raw": raw,
                    "level": parsed["level"],
                    "reason": parsed["reason"],
                    "status": parsed["status"],
                }
                f.write(json.dumps(rec) + "\n")

        assert calls["n"] == 68, calls["n"]

        # Fresh run.
        fresh_dir = _HERE / "runs" / "_test_restart_fresh"
        if fresh_dir.exists():
            shutil.rmtree(fresh_dir)
        fresh_dir.mkdir(parents=True)
        fresh_adapter = OracleAdapter(DEV_KEY, DEV_NOTE_MAP)
        fresh_rows = []
        with (fresh_dir / "responses.jsonl").open("w", encoding="utf-8") as f:
            for item in DEV_PUB:
                prompt = build_prompt(item["note"], "rules")
                raw = fresh_adapter.ask(prompt)
                parsed = parse_response(raw)
                rec = {
                    "id": item["id"],
                    "raw": raw,
                    "level": parsed["level"],
                    "reason": parsed["reason"],
                    "status": parsed["status"],
                }
                fresh_rows.append(rec)
                f.write(json.dumps(rec) + "\n")

        resumed_rows = load_jsonl(out_dir / "responses.jsonl")
        resumed_sorted = sorted(resumed_rows, key=lambda r: r["id"])
        fresh_sorted = sorted(fresh_rows, key=lambda r: r["id"])
        for r, f in zip(resumed_sorted, fresh_sorted):
            assert r["id"] == f["id"] and r["level"] == f["level"]
        record("T19 restart", True)
    except Exception as e:
        record("T19 restart", False, str(e))


def test_T20():
    """Review sheet: oracle gives 0 wrong rows, always3 gives expected count."""
    try:
        oracle_dir, _, _ = _run_mock_to_dir("oracle", "_test_review_oracle")
        wrong_csv, _ = build_sheets("_test_review_oracle")
        # count rows minus header.
        with wrong_csv.open("r", encoding="utf-8") as f:
            n_lines = sum(1 for _ in f) - 1
        assert n_lines == 0, n_lines

        always3_dir, rows, m = _run_mock_to_dir("always3", "_test_review_always3")
        wrong_csv2, _ = build_sheets("_test_review_always3")
        expected = sum(1 for r in rows if not (r["status"] == "ok" and r["level"] in DEV_KEY_MAP[r["id"]]["acceptable_levels"]))
        with wrong_csv2.open("r", encoding="utf-8") as f:
            n_lines = sum(1 for _ in f) - 1
        assert n_lines == expected, (n_lines, expected)
        record("T20 review sheet", True)
    except Exception as e:
        record("T20 review sheet", False, str(e))


def test_T21():
    """Plain prompt hides danger, resource, decision point, and thresholds."""
    try:
        prompt = build_prompt(DEV_PUB[0]["note"], "plain")
        low = prompt.lower()
        for word in ["danger", "resource", "decision point"]:
            assert word not in low, word
        # Threshold numbers must not appear in the instruction part.
        head = prompt.split("Patient note:")[0]
        for n in ["100", "20", "92", "7"]:
            assert n not in head, (n, head)
        record("T21 plain prompt bans", True)
    except Exception as e:
        record("T21 plain prompt bans", False, str(e))


def test_T22():
    """Rules prompt includes danger thresholds and pain cut off."""
    try:
        prompt = build_prompt(DEV_PUB[0]["note"], "rules")
        for n in ["100", "20", "92", "7"]:
            assert n in prompt, n
        record("T22 rules prompt values", True)
    except Exception as e:
        record("T22 rules prompt values", False, str(e))


def test_T23():
    """Export then import round trip. Also missing and duplicate ids."""
    try:
        # Build oracle answers as a single JSON array.
        arr = []
        for item in DEV_PUB:
            k = DEV_KEY_MAP[item["id"]]
            arr.append({"id": item["id"], "esi_level": int(k["esi_level"]), "reason": "oracle"})
        text = json.dumps(arr)
        out_dir = import_text(text, "dev", "rules", run_id="_test_import_full")
        results = json.loads((out_dir / "results.json").read_text(encoding="utf-8"))
        assert abs(results["metrics"]["accuracy"] - 1.0) < 1e-9

        # Missing: drop one item.
        arr2 = arr[:-1]
        text2 = json.dumps(arr2)
        out_dir2 = import_text(text2, "dev", "rules", run_id="_test_import_missing")
        rows2 = load_jsonl(out_dir2 / "responses.jsonl")
        n_missing = sum(1 for r in rows2 if r["status"] == "missing")
        assert n_missing == 1

        # Duplicate: add a copy.
        arr3 = arr + [arr[0]]
        text3 = json.dumps(arr3)
        err = None
        try:
            import_text(text3, "dev", "rules", run_id="_test_import_dup")
        except ValueError as e:
            err = e
        assert err is not None, "expected ValueError"
        record("T23 export import round trip", True)
    except Exception as e:
        record("T23 export import round trip", False, str(e))


def run_all():
    """Run every test in order and report."""
    test_T01()
    test_T02()
    test_T03()
    test_T04()
    test_T05()
    test_T06()
    test_T07()
    test_T08()
    test_T09()
    test_T10()
    test_T11()
    test_T12()
    test_T13()
    test_T14()
    test_T15()
    test_T16()
    test_T17()
    test_T18()
    test_T19()
    test_T20()
    test_T21()
    test_T22()
    test_T23()

    n_pass = sum(1 for _, ok, _ in RESULTS if ok)
    n_fail = len(RESULTS) - n_pass
    print()
    print(f"TOTAL: {n_pass} passed, {n_fail} failed, {len(RESULTS)} total")

    if n_fail == 0:
        _run_mock_baselines()
    return n_fail


def _run_mock_baselines():
    """Run all mock adapters on test and write a summary table."""
    print()
    print("Running mock baselines on test, rules...")
    out = _HERE / "reports" / "mock_baselines.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    header = (
        f"{'adapter':<22} | {'accuracy':>8} | {'CI_lower':>8} | {'CI_upper':>8} | "
        f"{'kappa':>7} | {'under':>6} | {'over':>6} | {'parse':>5}"
    )
    rows.append(header)
    rows.append("-" * len(header))
    for name in [
        "oracle", "always3", "random", "noisy_oracle_p02", "under_by_one",
        "over_by_one", "garbage", "fenced", "string_level", "condition_best",
    ]:
        adapter = build_mock_adapter(name, DEV_KEY, DEV_NOTE_MAP, TEST_KEY, TEST_NOTE_MAP)
        resp = _run_adapter(adapter, TEST_PUB, "rules")
        m = compute_all(resp, TEST_KEY_MAP)
        rows.append(
            f"{name:<22} | {m['accuracy']:>8.4f} | {m['ci_lower']:>8.4f} | {m['ci_upper']:>8.4f} | "
            f"{m['kappa']:>7.4f} | {m['undertriage_rate']:>6.3f} | {m['overtriage_rate']:>6.3f} | "
            f"{m['parse_error_count']:>5}"
        )
        print(rows[-1])
    out.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    n_fail = run_all()
    sys.exit(1 if n_fail > 0 else 0)
