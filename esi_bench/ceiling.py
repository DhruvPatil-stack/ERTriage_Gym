"""
Compute the Bayes ceiling and 3 baselines for any patient generator.
Usage: py ceiling.py [n_patients] [seed] [output_file]
Defaults: 10000 patients, seed 42, output to stdout only.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
from collections import defaultdict, Counter
from config import SEED, DANGER_HR, DANGER_RR, DANGER_SPO2, SEVERE_PAIN_THRESHOLD
from generator import generate_patient


def _group_key(p):
    """Build the visible group key from observable fields."""
    findings_id   = p.get("variant_id") or p.get("condition_name", "unknown")
    mental        = p["mental_status"]
    severe_pain   = int(p["pain_score"] >= SEVERE_PAIN_THRESHOLD)
    hr, rr, spo2  = p.get("heart_rate"), p.get("resp_rate"), p.get("spo2")
    if hr is None or rr is None or spo2 is None:
        dz = -1  # vital signs not obtainable
    else:
        dz = int(hr > DANGER_HR or rr > DANGER_RR or spo2 < DANGER_SPO2)
    return (findings_id, mental, severe_pain, dz)


def _ceiling_for(patients):
    """Return ceiling fraction for a list of patient dicts."""
    if not patients:
        return 1.0, 0
    groups = defaultdict(list)
    for p in patients:
        acceptable = p.get("acceptable_levels", [p["esi_level"]])
        groups[_group_key(p)].append(acceptable)

    matches = 0
    for acc_lists in groups.values():
        best = max(
            sum(1 for a in acc_lists if L in a)
            for L in range(1, 6)
        )
        matches += best
    return matches / len(patients), len(groups)


def compute(n=10_000, seed=SEED):
    """Generate n patients and return the metrics dict."""
    rng      = np.random.default_rng(seed)
    patients = [generate_patient(rng) for _ in range(n)]

    ceiling_all, n_groups = _ceiling_for(patients)

    nb = [p for p in patients if not p.get("is_borderline", False)]
    ceiling_nb, _ = _ceiling_for(nb)

    # Baseline A: always predict ESI 3
    b_always3 = sum(
        1 for p in patients
        if 3 in p.get("acceptable_levels", [p["esi_level"]])
    ) / n

    # Baseline B: per-condition most common label
    cond_counts = defaultdict(Counter)
    for p in patients:
        cond = p.get("condition_name", p.get("variant_id", "unknown"))
        cond_counts[cond][p["esi_level"]] += 1
    cond_best = {c: cnt.most_common(1)[0][0] for c, cnt in cond_counts.items()}
    b_cond = sum(
        1 for p in patients
        if cond_best.get(p.get("condition_name", p.get("variant_id", "unknown")))
        in p.get("acceptable_levels", [p["esi_level"]])
    ) / n

    # Baseline C: global most common label
    global_best = Counter(p["esi_level"] for p in patients).most_common(1)[0][0]
    b_global = sum(
        1 for p in patients
        if global_best in p.get("acceptable_levels", [p["esi_level"]])
    ) / n

    # ESI distribution
    dist = Counter(p["esi_level"] for p in patients)
    n_borderline = sum(1 for p in patients if p.get("is_borderline", False))

    return {
        "n":            n,
        "seed":         seed,
        "ceiling_all":  ceiling_all,
        "ceiling_nb":   ceiling_nb,
        "n_nb":         len(nb),
        "n_groups":     n_groups,
        "n_borderline": n_borderline,
        "b_always3":    b_always3,
        "b_cond":       b_cond,
        "b_global":     global_best,
        "b_global_pct": b_global,
        "dist":         dict(sorted(dist.items())),
    }


def report(m, label="", file=None):
    """Print a formatted report. Optionally write to file."""
    lines = []
    lines.append(f"=== Ceiling report{' — ' + label if label else ''} ===")
    lines.append(f"N = {m['n']:,}   seed = {m['seed']}")
    lines.append("")
    lines.append(f"Bayes ceiling (all patients):              {m['ceiling_all']*100:6.2f}%")
    lines.append(f"Bayes ceiling (non-borderline, n={m['n_nb']:,}): {m['ceiling_nb']*100:6.2f}%")
    lines.append(f"Borderline cases:                          {m['n_borderline']:,}")
    lines.append(f"Visible groups:                            {m['n_groups']:,}")
    lines.append("")
    lines.append("Baselines:")
    lines.append(f"  Always ESI 3:                            {m['b_always3']*100:6.2f}%")
    lines.append(f"  Per-condition best label:                {m['b_cond']*100:6.2f}%")
    lines.append(f"  Global best label (ESI {m['b_global']}):             {m['b_global_pct']*100:6.2f}%")
    lines.append("")
    lines.append("ESI distribution:")
    for lvl, cnt in m["dist"].items():
        lines.append(f"  ESI {lvl}: {cnt:5,}  ({cnt/m['n']*100:.1f}%)")

    text = "\n".join(lines)
    print(text)
    if file:
        os.makedirs(os.path.dirname(file), exist_ok=True)
        with open(file, "w") as f:
            f.write(text + "\n")
        print(f"\nSaved to {file}")


if __name__ == "__main__":
    n    = int(sys.argv[1]) if len(sys.argv) > 1 else 10_000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else SEED
    out  = sys.argv[3]      if len(sys.argv) > 3 else None
    m    = compute(n, seed)
    report(m, label="v1 (old generator)" if out and "v1" in out else "", file=out)
