"""
Unit tests for labeler.py.
Each test covers one decision point or one vital sign boundary.
Run with: py test_labeler.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from labeler import label, in_danger_zone
from config import DANGER_HR, DANGER_RR, DANGER_SPO2, SEVERE_PAIN_THRESHOLD


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
    }
    base.update(kw)
    return base


passed = 0
failed = 0


def check(description, got, expected):
    global passed, failed
    if got == expected:
        print(f"  PASS  {description}")
        passed += 1
    else:
        print(f"  FAIL  {description} -> got {got}, expected {expected}")
        failed += 1


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

print("\n=== Decision point B: severe pain ===")
check(f"pain={SEVERE_PAIN_THRESHOLD} gives ESI 2",
      label(make_pt(pain_score=SEVERE_PAIN_THRESHOLD)), 2)
check(f"pain={SEVERE_PAIN_THRESHOLD - 1} does NOT give ESI 2",
      label(make_pt(pain_score=SEVERE_PAIN_THRESHOLD - 1)), 3)

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

print(f"\n{'='*40}")
print(f"Result: {passed} passed, {failed} failed")
if failed > 0:
    sys.exit(1)
