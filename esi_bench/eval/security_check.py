"""Scan eval/*.py files for secrets and non-local network URLs.

The scanner looks for API key patterns and URLs that are not localhost 11434.
Output goes to eval/reports/security_check.txt.
"""
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent


KEY_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{10,}"),
    re.compile(r"OPENAI", re.IGNORECASE),
    re.compile(r"ANTHROPIC", re.IGNORECASE),
    re.compile(r"API_KEY", re.IGNORECASE),
]

URL_RE = re.compile(r"https?://[^\s'\"\)\\]+")


def _scan_file(path):
    """Return a dict of findings for one file."""
    text = path.read_text(encoding="utf-8", errors="replace")
    findings = {"keys": [], "urls": []}
    for pat in KEY_PATTERNS:
        for m in pat.finditer(text):
            findings["keys"].append((pat.pattern, m.group(0)))
    for m in URL_RE.finditer(text):
        url = m.group(0)
        if "localhost:11434" in url:
            continue
        if "localhost:19999" in url or "localhost:{port}" in url:
            continue
        if url.startswith("http://localhost:"):
            continue
        findings["urls"].append(url)
    return findings


def main():
    out_lines = ["ESI security scan", "-----------------"]
    issues = 0
    scanner_path = Path(__file__).resolve()
    for p in sorted(_HERE.rglob("*.py")):
        if "__pycache__" in str(p):
            continue
        if p.resolve() == scanner_path:
            continue
        f = _scan_file(p)
        if f["keys"] or f["urls"]:
            out_lines.append(f"\nFile: {p}")
            for pat, hit in f["keys"]:
                out_lines.append(f"  key pattern [{pat}]: {hit}")
                issues += 1
            for u in f["urls"]:
                out_lines.append(f"  url: {u}")
                issues += 1
    out_lines.append("")
    out_lines.append(f"total_issues: {issues}")
    out = _HERE / "reports" / "security_check.txt"
    out.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    print("\n".join(out_lines))
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
