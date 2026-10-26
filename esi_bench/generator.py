import numpy as np
from config import (
    HR_CLIP, RR_CLIP, SPO2_CLIP, AGE_RANGE,
    DANGER_HR, DANGER_RR, DANGER_SPO2,
    BORDERLINE_BAND, BORDERLINE_FRACTION,
)
from variants import VARIANTS, VARIANT_BY_ID, _VARIANT_WEIGHTS
from labeler import label

_VARIANT_INDEX = list(range(len(VARIANTS)))


def _clip(value, lo, hi):
    """Clip a value to [lo, hi]."""
    return int(max(lo, min(hi, round(value))))


def _draw_vital(rng, range_tuple, clip):
    """Draw a uniform integer from range_tuple and clip to valid bounds."""
    lo, hi = range_tuple
    return _clip(int(rng.integers(lo, hi + 1)), *clip)


def _apply_borderline(rng, hr, rr, spo2):
    """Nudge 1 vital sign to within BORDERLINE_BAND units of its danger limit."""
    vital = rng.choice(["hr", "rr", "spo2"])
    if vital == "hr":
        # Range spans the HR limit on both sides
        hr = _clip(
            int(rng.integers(DANGER_HR - BORDERLINE_BAND, DANGER_HR + BORDERLINE_BAND + 1)),
            *HR_CLIP,
        )
    elif vital == "rr":
        rr = _clip(
            int(rng.integers(DANGER_RR - BORDERLINE_BAND, DANGER_RR + BORDERLINE_BAND + 1)),
            *RR_CLIP,
        )
    else:
        spo2 = _clip(
            int(rng.integers(DANGER_SPO2 - BORDERLINE_BAND, DANGER_SPO2 + BORDERLINE_BAND + 1)),
            *SPO2_CLIP,
        )
    return hr, rr, spo2


def _build_note(p):
    """Build the observable text note from patient fields."""
    hr, rr, spo2 = p["heart_rate"], p["resp_rate"], p["spo2"]
    if hr is None:
        vitals_str = "Vital signs: not obtainable."
    else:
        vitals_str = f"Vital signs: HR {hr} bpm, RR {rr} breaths/min, SpO2 {spo2}%."
    return (
        f"A {p['age']}-year-old {p['sex']} presents with {p['complaint']}. "
        f"{p['findings']}. "
        f"{vitals_str} "
        f"Pain score: {p['pain_score']}/10. "
        f"Mental status: {p['mental_status']}."
    )


def generate_patient(rng, variant=None, borderline=None):
    """
    Generate one synthetic adult patient from the variant table.

    Parameters
    ----------
    rng       : numpy.random.Generator
    variant   : str or None  - variant_id (e.g. "V01"), or None for weighted random
    borderline: bool or None - True forces a borderline nudge, None uses BORDERLINE_FRACTION

    Returns
    -------
    dict with observable fields, hidden fields, esi_level, acceptable_levels, and note
    """
    # Select variant
    if variant is not None:
        v = VARIANT_BY_ID[variant]
    else:
        idx = int(rng.choice(_VARIANT_INDEX, p=_VARIANT_WEIGHTS))
        v = VARIANTS[idx]

    # Fixed hidden values from variant
    needs_immediate = v["needs_immediate"]
    high_risk       = v["high_risk"]
    resource_count  = v["resource_count"]

    # Demographics
    age_lo, age_hi = v.get("age_range", AGE_RANGE)
    age = int(rng.integers(age_lo, age_hi + 1))
    sex = rng.choice(["male", "female"])

    # Mental status
    mental_names = [c[0] for c in v["mental_choices"]]
    mental_probs = [c[1] for c in v["mental_choices"]]
    mental = str(rng.choice(mental_names, p=mental_probs))

    # Pain score
    p_lo, p_hi = v["pain_range"]
    pain = int(rng.integers(p_lo, p_hi + 1))

    # Complaint and findings phrasing
    complaint = str(rng.choice(v["complaints"]))
    findings  = str(rng.choice(v["findings"]))

    # Vital signs
    if v["hr_range"] is None:
        # Cardiac arrest with immediate flag: vitals not obtainable
        hr = rr = spo2 = None
    else:
        hr   = _draw_vital(rng, v["hr_range"],   HR_CLIP)
        rr   = _draw_vital(rng, v["rr_range"],   RR_CLIP)
        spo2 = _draw_vital(rng, v["spo2_range"], SPO2_CLIP)

    # Borderline nudge: only for designated borderline variants
    is_borderline = False
    if v["is_borderline_variant"] and hr is not None:
        apply_bl = borderline if borderline is not None else bool(rng.random() < BORDERLINE_FRACTION)
        if apply_bl:
            hr, rr, spo2 = _apply_borderline(rng, hr, rr, spo2)
            is_borderline = True

    patient = {
        # Observable fields
        "age":          age,
        "sex":          sex,
        "complaint":    complaint,
        "findings":     findings,
        "heart_rate":   hr,
        "resp_rate":    rr,
        "spo2":         spo2,
        "pain_score":   pain,
        "mental_status": mental,
        # Hidden fields (not in the text note)
        "needs_immediate": needs_immediate,
        "high_risk":       high_risk,
        "resource_count":  resource_count,
        # Metadata
        "variant_id":    v["variant_id"],
        "findings_id":   v["variant_id"],
        "condition_name": v["condition_name"],
        "typical_esi":   v["intended_esi"],
        "is_borderline": is_borderline,
    }

    esi = label(patient)
    patient["esi_level"] = esi
    patient["acceptable_levels"] = [2, 3] if is_borderline else [esi]
    patient["note"] = _build_note(patient)

    return patient
