from config import DANGER_HR, DANGER_RR, DANGER_SPO2, SEVERE_PAIN_THRESHOLD

# Mental status values that trigger ESI 2 at decision point B
_ALTERED = {"confused", "lethargic", "unresponsive"}


def in_danger_zone(patient):
    """Return True if any adult vital sign is in the ESI danger zone."""
    hr   = patient.get("heart_rate")
    rr   = patient.get("resp_rate")
    spo2 = patient.get("spo2")
    if hr is None or rr is None or spo2 is None:
        return False  # absent vitals (e.g. cardiac arrest) cannot be evaluated here
    return hr > DANGER_HR or rr > DANGER_RR or spo2 < DANGER_SPO2


def label(patient):
    """Apply the ESI algorithm and return an integer level 1-5."""

    # Point A: immediate life-saving intervention needed
    if patient["needs_immediate"]:
        return 1

    # Point B: high-risk situation, altered mental status, or severe pain
    altered     = patient["mental_status"] in _ALTERED
    severe_pain = patient["pain_score"] >= SEVERE_PAIN_THRESHOLD
    if patient["high_risk"] or altered or severe_pain:
        return 2

    # Point C: count resources
    r = patient["resource_count"]
    if r == 0:
        return 5
    if r == 1:
        return 4

    # Point D: 2 or more resources - check danger zone
    if in_danger_zone(patient):
        return 2  # simplification: danger zone is automatic ESI 2, not "consider" - VERIFY
    return 3
