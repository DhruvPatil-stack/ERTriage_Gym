"""
Generate 10,000 patients and report the ESI level distribution.
Compare actual shares to the target mix in config.py.
Run with: py check_distribution.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
from config import SEED, TARGET_MIX
from generator import generate_patient

N = 10_000
rng = np.random.default_rng(SEED)

counts       = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
mismatch     = 0
borderline   = 0
errors       = 0

for _ in range(N):
    try:
        p = generate_patient(rng)
        counts[p["esi_level"]] += 1
        if p["typical_esi"] != p["esi_level"]:
            mismatch += 1
        if p["is_borderline"]:
            borderline += 1
    except Exception as e:
        errors += 1
        print(f"ERROR: {e}")

print(f"\nESI distribution over {N} patients (seed={SEED})")
print(f"{'Level':<8} {'Target':>8} {'Actual':>8} {'Diff':>8} {'Status'}")
print("-" * 46)
all_ok = True
for lvl in range(1, 6):
    target  = TARGET_MIX[lvl] * 100
    actual  = counts[lvl] / N * 100
    diff    = actual - target
    ok      = abs(diff) <= 5.0
    status  = "OK" if ok else "OUTSIDE 5pp"
    if not ok:
        all_ok = False
    print(f"  ESI {lvl}   {target:>7.1f}%  {actual:>7.1f}%  {diff:>+7.1f}%   {status}")

print("-" * 46)
print(f"\nMismatches (typical_esi != labeler): {mismatch} ({mismatch/N*100:.1f}%)")
print(f"Borderline cases:                    {borderline} ({borderline/N*100:.1f}%)")
print(f"Generator errors:                    {errors}")
print(f"\nAll ESI levels within 5pp of target: {'YES' if all_ok else 'NO'}")
print(f"All ESI levels appear at least once:  {'YES' if all(v > 0 for v in counts.values()) else 'NO'}")
