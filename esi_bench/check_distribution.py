"""
Generate 10,000 patients and report the ESI distribution, variant counts, and borderline count.
The code does not compare against TARGET_MIX. TARGET_MIX is a reference value only.
Run with: py check_distribution.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
from collections import Counter
from config import SEED
from generator import generate_patient
from variants import VARIANTS

N = 10_000
rng = np.random.default_rng(SEED)

esi_counts     = Counter()
variant_counts = Counter()
borderline     = 0
errors         = 0

for _ in range(N):
    try:
        p = generate_patient(rng)
        esi_counts[p["esi_level"]] += 1
        variant_counts[p["variant_id"]] += 1
        if p["is_borderline"]:
            borderline += 1
    except Exception as e:
        errors += 1
        print(f"ERROR: {e}")

print(f"\nESI distribution over {N} patients (seed={SEED})")
print(f"{'Level':<8} {'Count':>7} {'Share':>8}")
print("-" * 28)
for lvl in range(1, 6):
    cnt = esi_counts.get(lvl, 0)
    print(f"  ESI {lvl}   {cnt:>6,}   {cnt/N*100:>6.1f}%")

print(f"\nVariant counts (each must appear at least 10 times)")
print(f"{'Variant':<10} {'ESI':>5} {'Count':>7}")
print("-" * 26)
all_ok = True
for v in VARIANTS:
    vid = v["variant_id"]
    cnt = variant_counts.get(vid, 0)
    flag = "" if cnt >= 10 else "  <-- BELOW 10"
    if cnt < 10:
        all_ok = False
    print(f"  {vid:<8}  ESI {v['intended_esi']}  {cnt:>6,}{flag}")

print(f"\nBorderline cases: {borderline} ({borderline/N*100:.1f}%)")
print(f"Generator errors: {errors}")
print(f"\nAll variants appear at least 10 times: {'YES' if all_ok else 'NO'}")
print(f"All 5 ESI levels present:              {'YES' if all(esi_counts.get(l,0)>0 for l in range(1,6)) else 'NO'}")
