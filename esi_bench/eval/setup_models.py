"""Choose and pull Ollama models for the benchmark.

The script reads hardware.txt, picks three model tags, and runs ollama pull.
Model digests go to eval/reports/models.txt.
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _parse_hardware():
    """Read eval/reports/hardware.txt and return RAM in GB, else None."""
    path = _HERE / "reports" / "hardware.txt"
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("total_ram_gb:"):
            val = line.split(":", 1)[1].strip()
            try:
                return float(val)
            except Exception:
                return None
    return None


def _ollama_running():
    """Return True if the local server responds."""
    import urllib.request
    try:
        with urllib.request.urlopen("http://localhost:11434/", timeout=5) as r:
            r.read(32)
        return True
    except Exception:
        return False


def _ollama_installed():
    """Return True if the ollama binary exists."""
    try:
        res = subprocess.run(["ollama", "--version"], capture_output=True, text=True, timeout=10)
        return res.returncode == 0
    except Exception:
        return False


def _pick_models(ram_gb):
    """Pick model tags based on total RAM. CPU-only hosts need light tags."""
    # On CPU-only machines we stay small for time budget.
    if ram_gb is None or ram_gb < 6:
        return []
    if ram_gb < 12:
        return ["llama3.2:3b", "qwen2.5:3b", "phi4-mini:3.8b"]
    if ram_gb < 24:
        return ["llama3.2:3b", "qwen2.5:7b", "llama3.1:8b"]
    # 24+ GB. Still favor small for CPU-only time budget.
    return ["llama3.2:3b", "qwen2.5:7b", "llama3.1:8b"]


def _list_local():
    """Return a list of (tag, digest, size) tuples for installed models."""
    try:
        res = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=20)
        if res.returncode != 0:
            return []
        out = []
        for line in res.stdout.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 4:
                tag = parts[0]
                digest = parts[1]
                size = parts[2] + " " + parts[3]
                out.append((tag, digest, size))
        return out
    except Exception:
        return []


def _pull_model(tag):
    """Run ollama pull and return True on success."""
    try:
        res = subprocess.run(
            ["ollama", "pull", tag],
            capture_output=True, text=True, timeout=1800,
            encoding="utf-8", errors="replace",
        )
        log = (res.stdout or "") + (res.stderr or "")
        return res.returncode == 0, log
    except Exception as e:
        return False, str(e)


def _write_blocked(msg):
    """Write BLOCKED.md and print."""
    path = _HERE / "reports" / "BLOCKED.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# BLOCKED\n\n{msg}\n", encoding="utf-8")
    print(f"BLOCKED: {msg}")


def main():
    ram = _parse_hardware()
    if not _ollama_installed():
        _write_blocked("Ollama not installed. Run: winget install Ollama.Ollama. Then run: ollama serve")
        return 1
    if not _ollama_running():
        _write_blocked("Ollama server not running. Run: ollama serve")
        return 1
    if ram is None or ram < 6:
        _write_blocked("RAM too low for local models. Mock results only.")
        return 1

    picks = _pick_models(ram)
    local = _list_local()
    local_tags = {t for t, _, _ in local}

    out_lines = ["ESI benchmark model setup", "-------------------------", f"ram_gb: {ram:.2f}"]
    out_lines.append(f"planned_models: {', '.join(picks)}")
    out_lines.append("")

    results = []
    for tag in picks:
        if tag in local_tags:
            out_lines.append(f"{tag}: already present")
            results.append((tag, "present"))
            continue
        print(f"Pulling {tag} ...")
        ok, log = _pull_model(tag)
        tail = log.strip().splitlines()[-1] if log.strip() else ""
        if ok:
            out_lines.append(f"{tag}: pulled ({tail})")
            results.append((tag, "pulled"))
        else:
            out_lines.append(f"{tag}: FAIL ({tail})")
            results.append((tag, "fail"))

    # Record digests for the models we have.
    out_lines.append("")
    out_lines.append("Installed model digests:")
    for t, d, s in _list_local():
        out_lines.append(f"  {t}  {d}  {s}")

    out_path = _HERE / "reports" / "models.txt"
    out_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    print("\n".join(out_lines))
    print(f"Wrote {out_path}")

    # Record failures to BLOCKED if any.
    failed = [t for t, s in results if s == "fail"]
    if failed:
        _write_blocked(f"Model pull failed for: {', '.join(failed)}. Run: ollama pull <tag> manually.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
