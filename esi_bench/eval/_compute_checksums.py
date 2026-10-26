"""Compute SHA-256 of selected source files.

The script writes one hash per line to reports/checksums_before.txt.
It covers Layer 1 files and all esi_bench .py and README files.
It excludes the _step2_backup folder.
"""
import hashlib
from pathlib import Path
import sys


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main(out_path: str) -> None:
    layer1 = Path("C:/Users/dhruv/Desktop/Master_Projects/ER_Triage_Gym")
    bench = Path("C:/Users/dhruv/Desktop/Master_Projects/ER_Triage_Gym/esi_bench")
    files = []
    for name in ["triage_gym.py", "test_triage.py", "train.py", "evaluate.py", "requirements.txt"]:
        p = layer1 / name
        if p.exists():
            files.append(p)
    for p in sorted(bench.glob("*.py")):
        if "_step2_backup" in str(p):
            continue
        files.append(p)
    rp = bench / "README.md"
    if rp.exists():
        files.append(rp)
    lines = []
    for p in files:
        if "_step2_backup" in str(p):
            continue
        lines.append(f"{sha256_file(p)}  {p.as_posix()}")
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(lines)} hashes to {out}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "eval/reports/checksums_before.txt")
