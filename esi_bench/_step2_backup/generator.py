import numpy as np
from config import (
    HR_CLIP, RR_CLIP, SPO2_CLIP, PAIN_CLIP, AGE_RANGE,
    DANGER_HR, DANGER_RR, DANGER_SPO2,
    SEVERE_PAIN_THRESHOLD, BORDERLINE_FRACTION,
)
from conditions import CONDITIONS, CONDITION_BY_NAME
from labeler import label, in_danger_zone

# Mental status values that trigger ESI 2 at decision point B
_ALTERED = {"confused", "lethargic", "unresponsive"}

_CONDITION_WEIGHTS = np.array([c["weight"] for c in CONDITIONS])
_CONDITION_NAMES   = [c["name"] for c in CONDITIONS]


def _clip(value, lo, hi):
    """Clip a value to [lo, hi]."""
    return int(max(lo, min(hi, round(value))))


def _pick_condition(rng, name=None):
    """Return one condition dict by name or by weighted random draw."""
    if name is not None:
        return CONDITION_BY_NAME[name]
    idx = rng.choice(len(CONDITIONS), p=_CONDITION_WEIGHTS)
    return CONDITIONS[idx]


def _draw_vitals(rng, cond):
    """Draw heart rate, respiratory rate, and SpO2 from condition distributions."""
    hr   = _clip(rng.normal(cond["hr_mean"],   cond["hr_sd"]),   *HR_CLIP)
    rr   = _clip(rng.normal(cond["rr_mean"],   cond["rr_sd"]),   *RR_CLIP)
    spo2 = _clip(rng.normal(cond["spo2_mean"], cond["spo2_sd"]), *SPO2_CLIP)
    return hr, rr, spo2


def _draw_mental_status(rng, cond):
    """Draw mental status from the condition's weighted choice list."""
    choices = cond["mental_status_choices"]
    names   = [c[0] for c in choices]
    probs   = [c[1] for c in choices]
    return rng.choice(names, p=probs)


def _apply_borderline(rng, hr, rr, spo2):
    """Nudge one vital sign to within 3 units of its danger zone threshold."""
    vital = rng.choice(["hr", "rr", "spo2"])
    if vital == "hr":
        # Set HR within [DANGER_HR - 2, DANGER_HR + 3]
        hr = _clip(rng.integers(DANGER_HR - 2, DANGER_HR + 4), *HR_CLIP)
    elif vital == "rr":
        rr = _clip(rng.integers(DANGER_RR - 2, DANGER_RR + 4), *RR_CLIP)
    else:
        # SpO2 danger is below threshold, so nudge to [threshold - 2, threshold + 3]
        spo2 = _clip(rng.integers(DANGER_SPO2 - 2, DANGER_SPO2 + 4), *SPO2_CLIP)
    return hr, rr, spo2


def _build_note(patient):
    """Build the observable text note. The note does not include hidden fields."""
    age      = patient["age"]
    sex      = patient["sex"]
    complaint = patient["complaint"]
    hr       = patient["heart_rate"]
    rr       = patient["resp_rate"]
    spo2     = patient["spo2"]
    pain     = patient["pain_score"]
    mental   = patient["mental_status"]

    if hr is None:
        vitals_str = "Vital signs: not obtainable."
    else:
        vitals_str = (
            f"Vital signs: HR {hr} bpm, RR {rr} breaths/min, SpO2 {spo2}%."
        )

    return (
        f"A {age}-year-old {sex} presents with {complaint}. "
        f"{vitals_str} "
        f"Pain score: {pain}/10. "
        f"Mental status: {mental}."
    )


def generate_patient(rng, condition=None, borderline=None):
    """
    Generate one synthetic adult patient.

    Parameters
    ----------
    rng       : numpy.random.Generator
    condition : str or None - condition name, or None for a random draw
    borderline: bool or None - True forces a borderline vital, None uses BORDERLINE_FRACTION

    Returns
    -------
    dict with observable fields, hidden fields, ESI label, and the text note
    """
    cond = _pick_condition(rng, condition)

    # Hidden flags
    needs_immediate = bool(rng.random() < cond["p_immediate"])
    high_risk = (not needs_immediate) and bool(rng.random() < cond["p_high_risk"])

    # Demographics
    age_lo, age_hi = cond.get("age_range", AGE_RANGE)
    age = int(rng.integers(age_lo, age_hi + 1))
    sex = rng.choice(["male", "female"])

    # Mental status
    mental = _draw_mental_status(rng, cond)

    # Vital signs - cardiac arrest with immediate flag uses extreme or None vitals
    if needs_immediate and cond["name"] == "cardiac_arrest":
        hr, rr, spo2 = None, None, None
    else:
        hr, rr, spo2 = _draw_vitals(rng, cond)

    # Pain score
    pain_lo, pain_hi = cond["pain_range"]
    pain = int(rng.integers(pain_lo, pain_hi + 1))

    # Resource count
    r_weights = cond["resource_weights"]
    resource_count = int(rng.choice([0, 1, 2, 3], p=r_weights))

    # Decide if borderline nudge applies (only for patients that reach decision point D)
    at_B = (high_risk
            or mental in _ALTERED
            or pain >= SEVERE_PAIN_THRESHOLD)
    at_D = (not needs_immediate) and (not at_B) and (resource_count >= 2)

    is_borderline = False
    if at_D:
        force_bl = borderline if borderline is not None else (rng.random() < BORDERLINE_FRACTION)
        if force_bl and hr is not None:
            hr, rr, spo2 = _apply_borderline(rng, hr, rr, spo2)
            is_borderline = True

    patient = {
        # Observable fields
        "age":           age,
        "sex":           sex,
        "condition_name": cond["name"],
        "complaint":     cond["complaint"],
        "heart_rate":    hr,
        "resp_rate":     rr,
        "spo2":          spo2,
        "pain_score":    pain,
        "mental_status": mental,
        # Hidden fields
        "needs_immediate": needs_immediate,
        "high_risk":       high_risk,
        "resource_count":  resource_count,
        # Metadata
        "typical_esi":   cond["typical_esi"],
        "is_borderline": is_borderline,
    }

    # Label uses all fields including hidden ones
    patient["esi_level"] = label(patient)
    patient["note"]      = _build_note(patient)

    return patient
