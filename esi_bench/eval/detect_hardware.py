"""Detect hardware for model selection.

The script reads RAM, free disk, GPU, and CPU count on Windows.
Output goes to eval/reports/hardware.txt.
"""
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _get_total_ram_gb():
    """Return total RAM in GB using wmic, else PowerShell CIM."""
    try:
        res = subprocess.run(
            ["wmic", "computersystem", "get", "TotalPhysicalMemory"],
            capture_output=True, text=True, timeout=15,
        )
        if res.returncode == 0:
            lines = [ln.strip() for ln in res.stdout.splitlines() if ln.strip()]
            for ln in lines:
                if ln.isdigit():
                    return int(ln) / (1024 ** 3)
    except Exception:
        pass
    try:
        res = subprocess.run(
            [
                "powershell", "-NoProfile", "-Command",
                "(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory",
            ],
            capture_output=True, text=True, timeout=20,
        )
        if res.returncode == 0:
            out = res.stdout.strip()
            if out.isdigit():
                return int(out) / (1024 ** 3)
    except Exception:
        pass
    return None


def _get_free_disk_gb(root="C:/"):
    """Return free disk space in GB."""
    try:
        d = shutil.disk_usage(root)
        return d.free / (1024 ** 3)
    except Exception:
        return None


def _get_gpu_info():
    """Return GPU info string from nvidia-smi, else a status line."""
    try:
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10,
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
        return "no NVIDIA GPU detected"
    except FileNotFoundError:
        return "nvidia-smi not found"
    except Exception as e:
        return f"gpu check failed: {e}"


def _get_cpu_count():
    """Return the logical CPU count."""
    return os.cpu_count()


def main():
    ram_gb = _get_total_ram_gb()
    disk_gb = _get_free_disk_gb("C:/")
    gpu = _get_gpu_info()
    cpu = _get_cpu_count()
    sys_name = platform.system()
    sys_rel = platform.release()
    sys_ver = platform.version()
    machine = platform.machine()
    py_ver = platform.python_version()

    lines = [
        "ESI benchmark hardware report",
        "-----------------------------",
        f"platform: {sys_name} {sys_rel}",
        f"version: {sys_ver}",
        f"machine: {machine}",
        f"python: {py_ver}",
        f"cpu_count: {cpu}",
        f"total_ram_gb: {ram_gb:.2f}" if ram_gb is not None else "total_ram_gb: unknown",
        f"free_disk_c_gb: {disk_gb:.2f}" if disk_gb is not None else "free_disk_c_gb: unknown",
        f"gpu: {gpu}",
    ]
    out = _HERE / "reports" / "hardware.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
