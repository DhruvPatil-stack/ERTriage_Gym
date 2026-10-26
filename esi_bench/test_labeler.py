"""
Unit tests for labeler.py, generator.py, and variants.py.
Run with: py test_labeler.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import re
import numpy as np
from labeler import label, in_danger_zone, is_correct
from generator import generate_patient
from variants import VARIANTS, VARIANT_BY_ID
from config import (
    DANGER_HR, DANGER_RR, DANGER_SPO2,
    SEVERE_PAIN_THRESHOLD,
    BORDERLINE_BAND, BORDERLINE_FRACTION, SEED,
    MARGIN_HR, MARGIN_RR, MARGIN_SPO2,
)

passed = 0
failed = 0

# Restricted words must not appear as whole words in any note (design rule D3)
# Use word boundaries to avoid matching substrings inside medical terms
# e.g. "diaphoresis" contains "esi" but is not a banned word
_BANNED_PATTERNS = [re.compile(r'\b' + re.escape(w) + r'\b', re.IGNORECASE)
                    for w in ["ESI", "high risk", "resource", "triage", "life-saving"]]


def check(desc, got, expected):
    global passed, failed
    if got == expected:
        print(f"  PASS  {desc}")
        passed += 1
    else:
        print(f"  FAIL  {desc} -> got {got}, expected {expected}")
        failed += 1


def check_true(desc, value):
    global passed, failed
    if value:
        print(f"  PASS  {desc}")
        passed += 1
    else:
        print(f"  FAIL  {desc} -> got False")
        failed += 1


def make_pt(**kw):
    """Build a base ESI 3 patient and apply overrides."""
    base = {
        "needs_immediate": False,
        "high_risk":       False,
        "mental_status":   "alert",
        "pain_score":      3,
        "resource_count":  2,
        "heart_rate":      80,
        "resp_rate":       16,
        "spo2":            98,
        "acceptable_levels": [3],
    }
    base.update(kw)
    return base


# ── Original labeler tests (pain threshold updated from 8 to 7 per D6) ────────

print("=== Decision point A: immediate ===")
check("needs_immediate=True gives ESI 1",
      label(make_pt(needs_immediate=True)), 1)
check("needs_immediate=False does not give ESI 1 by itself",
      label(make_pt(needs_immediate=False)), 3)

print("\n=== Decision point B: high_risk ===")
check("high_risk=True gives ESI 2",
      label(make_pt(high_risk=True)), 2)

print("\n=== Decision point B: altered mental status ===")
check("confused gives ESI 2",
      label(make_pt(mental_status="confused")), 2)
check("lethargic gives ESI 2",
      label(make_pt(mental_status="lethargic")), 2)
check("unresponsive gives ESI 2",
      label(make_pt(mental_status="unresponsive")), 2)
check("anxious does NOT give ESI 2",
      label(make_pt(mental_status="anxious")), 3)
check("alert does NOT give ESI 2",
      label(make_pt(mental_status="alert")), 3)

print("\n=== Decision point B: pain (threshold now 7 per D6) ===")
check(f"pain={SEVERE_PAIN_THRESHOLD} gives ESI 2",
      label(make_pt(pain_score=SEVERE_PAIN_THRESHOLD)), 2)
check(f"pain={SEVERE_PAIN_THRESHOLD - 1} does NOT give ESI 2",
      label(make_pt(pain_score=SEVERE_PAIN_THRESHOLD - 1)), 3)
check("pain=8 also gives ESI 2",
      label(make_pt(pain_score=8)), 2)
check("pain=6 does NOT give ESI 2",
      label(make_pt(pain_score=6)), 3)

print("\n=== Decision point C: resource count ===")
check("resource_count=0 gives ESI 5",
      label(make_pt(resource_count=0)), 5)
check("resource_count=1 gives ESI 4",
      label(make_pt(resource_count=1)), 4)

print("\n=== Decision point D: stable gives ESI 3 ===")
check("resource_count=2, normal vitals gives ESI 3",
      label(make_pt(resource_count=2)), 3)
check("resource_count=3, normal vitals gives ESI 3",
      label(make_pt(resource_count=3)), 3)

print("\n=== Decision point D: heart rate boundary ===")
check(f"HR={DANGER_HR + 1} (above threshold) gives ESI 2",
      label(make_pt(heart_rate=DANGER_HR + 1)), 2)
check(f"HR={DANGER_HR} (at threshold, not above) gives ESI 3",
      label(make_pt(heart_rate=DANGER_HR)), 3)

print("\n=== Decision point D: respiratory rate boundary ===")
check(f"RR={DANGER_RR + 1} (above threshold) gives ESI 2",
      label(make_pt(resp_rate=DANGER_RR + 1)), 2)
check(f"RR={DANGER_RR} (at threshold, not above) gives ESI 3",
      label(make_pt(resp_rate=DANGER_RR)), 3)

print("\n=== Decision point D: SpO2 boundary ===")
check(f"SpO2={DANGER_SPO2 - 1} (below threshold) gives ESI 2",
      label(make_pt(spo2=DANGER_SPO2 - 1)), 2)
check(f"SpO2={DANGER_SPO2} (at threshold, not below) gives ESI 3",
      label(make_pt(spo2=DANGER_SPO2)), 3)

print("\n=== in_danger_zone helper ===")
check("None vitals return False",
      in_danger_zone({"heart_rate": None, "resp_rate": None, "spo2": None}), False)
check("All normal vitals return False",
      in_danger_zone({"heart_rate": 80, "resp_rate": 16, "spo2": 98}), False)
check("High HR alone returns True",
      in_danger_zone({"heart_rate": 101, "resp_rate": 16, "spo2": 98}), True)
check("Low SpO2 alone returns True",
      in_danger_zone({"heart_rate": 80, "resp_rate": 16, "spo2": 91}), True)

print("\n=== is_correct helper ===")
p_ex = make_pt(acceptable_levels=[2, 3], esi_level=3)
check("is_correct: answer in acceptable_levels returns True",
      is_correct(2, p_ex), True)
check("is_correct: answer not in acceptable_levels returns False",
      is_correct(4, p_ex), False)

# ── New tests ──────────────────────────────────────────────────────────────────

print("\n=== Variant intent: labeler must equal intended_esi (borderline=False) ===")
rng_vi = np.random.default_rng(SEED)
intent_failures = []
for v in VARIANTS:
    mismatches = 0
    for _ in range(200):
        p = generate_patient(rng_vi, variant=v["variant_id"], borderline=False)
        if p["esi_level"] != v["intended_esi"]:
            mismatches += 1
    if mismatches > 0:
        intent_failures.append(f"{v['variant_id']} ({mismatches}/200 wrong)")
    check(f"{v['variant_id']} intended_esi={v['intended_esi']}",
          mismatches, 0)

print("\n=== No leak: banned words must not appear in any note ===")
rng_nl = np.random.default_rng(SEED)
leak_found = False
for _ in range(2000):
    p = generate_patient(rng_nl)
    note_lower = p["note"].lower()
    for pat in _BANNED_PATTERNS:
        m = pat.search(p["note"])
        if m:
            print(f"  FAIL  banned word '{m.group()}' in note: {p['note'][:80]}")
            leak_found = True
            failed += 1
if not leak_found:
    print(f"  PASS  no banned words found in 2000 notes")
    passed += 1

print("\n=== Borderline: acceptable_levels, labeler result, and nudge range ===")
rng_bl = np.random.default_rng(SEED)
borderline_variants = [v for v in VARIANTS if v["is_borderline_variant"]]
bl_errors = 0
for v in borderline_variants:
    for _ in range(100):
        p = generate_patient(rng_bl, variant=v["variant_id"], borderline=True)
        # acceptable_levels must be [2, 3]
        if p["acceptable_levels"] != [2, 3]:
            bl_errors += 1
        # labeler result must be 2 or 3
        if p["esi_level"] not in (2, 3):
            bl_errors += 1
        # nudged vital must be within BORDERLINE_BAND of its limit
        hr, rr, spo2 = p["heart_rate"], p["resp_rate"], p["spo2"]
        if hr is not None:
            near = (
                abs(hr   - DANGER_HR)   <= BORDERLINE_BAND or
                abs(rr   - DANGER_RR)   <= BORDERLINE_BAND or
                abs(spo2 - DANGER_SPO2) <= BORDERLINE_BAND
            )
            if not near:
                bl_errors += 1
check("borderline patients: acceptable_levels=[2,3], esi in {2,3}, nudge within band",
      bl_errors, 0)

print("\n=== Non-borderline: acceptable_levels has exactly 1 level ===")
rng_nb = np.random.default_rng(SEED)
nb_errors = 0
for _ in range(2000):
    p = generate_patient(rng_nb, borderline=False)
    if p["is_borderline"]:
        nb_errors += 1
    if len(p["acceptable_levels"]) != 1:
        nb_errors += 1
check("non-borderline patients have 1 acceptable level and is_borderline=False",
      nb_errors, 0)

print("\n=== Determinism: same seed gives same patients ===")
rng_a = np.random.default_rng(SEED)
rng_b = np.random.default_rng(SEED)
det_errors = 0
for _ in range(500):
    pa = generate_patient(rng_a)
    pb = generate_patient(rng_b)
    if pa["note"] != pb["note"] or pa["esi_level"] != pb["esi_level"]:
        det_errors += 1
check("500 patients from same seed are identical", det_errors, 0)

print("\n=== Vital ranges: all variant ranges respect MARGIN from danger limits ===")
margin_errors = []
for v in VARIANTS:
    vid = v["variant_id"]
    hr_r, rr_r, spo2_r = v["hr_range"], v["rr_range"], v["spo2_range"]
    if hr_r is None:
        continue  # V01 cardiac arrest with no vitals
    hr_lo, hr_hi = hr_r
    rr_lo, rr_hi = rr_r
    spo2_lo, spo2_hi = spo2_r
    # For stable ranges: max must be <= DANGER_HR - MARGIN_HR
    # For danger ranges: min must be >= DANGER_HR + MARGIN_HR
    # A range is "danger" if its min is above DANGER_HR (for HR)
    if hr_hi <= DANGER_HR:  # stable HR range
        if DANGER_HR - hr_hi < MARGIN_HR:
            margin_errors.append(f"{vid}: HR hi={hr_hi} is within {MARGIN_HR} of limit")
    else:  # danger HR range (min > DANGER_HR)
        if hr_lo - DANGER_HR < MARGIN_HR:
            margin_errors.append(f"{vid}: HR lo={hr_lo} is within {MARGIN_HR} of limit")

    if rr_hi <= DANGER_RR:
        if DANGER_RR - rr_hi < MARGIN_RR:
            margin_errors.append(f"{vid}: RR hi={rr_hi} is within {MARGIN_RR} of limit")
    else:
        if rr_lo - DANGER_RR < MARGIN_RR:
            margin_errors.append(f"{vid}: RR lo={rr_lo} is within {MARGIN_RR} of limit")

    if spo2_lo >= DANGER_SPO2:  # stable SpO2
        if spo2_lo - DANGER_SPO2 < MARGIN_SPO2:
            margin_errors.append(f"{vid}: SpO2 lo={spo2_lo} is within {MARGIN_SPO2} of limit")
    else:  # danger SpO2 (max < DANGER_SPO2)
        if DANGER_SPO2 - spo2_hi < MARGIN_SPO2:
            margin_errors.append(f"{vid}: SpO2 hi={spo2_hi} is within {MARGIN_SPO2} of limit")

for e in margin_errors:
    print(f"  FAIL  margin: {e}")
    failed += 1
if not margin_errors:
    print(f"  PASS  all variant vital ranges respect MARGIN from danger limits")
    passed += 1

print(f"\n{'='*44}")
print(f"Result: {passed} passed, {failed} failed")
if failed > 0:
    sys.exit(1)
