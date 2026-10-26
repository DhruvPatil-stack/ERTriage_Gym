"""Recompute SHA-256 for every file listed in checksums_before.txt.

The script writes eval/reports/checksums_after.txt. It also marks any mismatch.
"""
import hashlib
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _sha256_file(p):
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    before_path = _HERE / "reports" / "checksums_before.txt"
    lines = before_path.read_text(encoding="utf-8").splitlines()
    out_lines = []
    mismatches = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        old_hash, path_str = parts[0], parts[1]
        path = Path(path_str)
        if not path.exists():
            out_lines.append(f"MISSING  {path_str}  (was {old_hash})")
            mismatches.append(path_str)
            continue
        new_hash = _sha256_file(path)
        tag = "OK " if new_hash == old_hash else "DIFF"
        if new_hash != old_hash:
            mismatches.append(path_str)
        out_lines.append(f"{new_hash}  {path_str}  {tag}")

    out_path = _HERE / "reports" / "checksums_after.txt"
    out_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    print("\n".join(out_lines))
    if mismatches:
        print()
        print(f"Mismatches: {len(mismatches)}")
        for m in mismatches:
            print(f"  {m}")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
