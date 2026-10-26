"""Prompt builder for the two conditions.

The "rules" prompt gives the four ESI decision points and the thresholds.
The "plain" prompt gives only the scale direction and the output format.
Both prompts hide the key fields and omit the words borderline and key.
"""
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_BENCH = _HERE.parent
if str(_BENCH) not in sys.path:
    sys.path.insert(0, str(_BENCH))

from config import DANGER_HR, DANGER_RR, DANGER_SPO2, SEVERE_PAIN_THRESHOLD  # noqa: E402


# Resource list for the rules prompt. # VERIFY
RESOURCE_LIST = (
    "Resources that count: labs, ECG, X-ray, CT, MRI, ultrasound, IV fluids, "
    "IV or IM or nebulized medicine, specialty consult, simple procedure (one resource), "
    "complex procedure (two resources). "
    "Items that do not count: history and physical exam, point-of-care tests, saline lock, "
    "oral medicine, tetanus shot, prescription refill, simple wound care, crutches, splints, slings."
)


_HEADER = (
    "You are an emergency room triage nurse. "
    "Rate the patient on the ESI scale. "
    "The scale runs from one to five. "
    "One means the most urgent case. "
    "Five means the least urgent case. "
    "Return one JSON object. "
    "The object has two fields. "
    "Field esi_level is an integer from one to five. "
    "Field reason is one short sentence. "
    "Example: {\"esi_level\": 3, \"reason\": \"stable vitals and two tests\"}."
)


def _rules_body():
    """Build the rules body with thresholds pulled from config."""
    return (
        "\n\nESI procedure:\n"
        "Point A: the patient needs immediate life-saving action. Rate as one.\n"
        "Point B: high risk, altered mental state, or severe pain. Rate as two.\n"
        "Point C: count the resources. Zero resources rates as five. One resource rates as four.\n"
        "Point D: two or more resources. Check the vital signs.\n"
        "\n"
        f"Danger zone values: heart rate above {DANGER_HR} bpm, "
        f"respiratory rate above {DANGER_RR} breaths per minute, "
        f"oxygen saturation below {DANGER_SPO2} percent.\n"
        f"Severe pain starts at pain score {SEVERE_PAIN_THRESHOLD} or higher.\n"
        "Altered mental states: confused, lethargic, unresponsive.\n"
        "A value exactly at the limit is not in the danger zone.\n"
        "A patient in the danger zone rates as two.\n"
        "\n"
        + RESOURCE_LIST
    )


def build_prompt(note: str, condition: str) -> str:
    """Return the full prompt text for the given note and condition."""
    if condition not in ("rules", "plain"):
        raise ValueError(f"unknown condition: {condition}")
    body = _HEADER
    if condition == "rules":
        body = body + _rules_body()
    return body + "\n\nPatient note:\n" + note


def validate_prompts() -> None:
    """Check that both prompts obey the ban lists."""
    sample_note = "A 40-year-old female presents with sore throat."
    rules = build_prompt(sample_note, "rules")
    plain = build_prompt(sample_note, "plain")

    for text, name in [(rules, "rules"), (plain, "plain")]:
        low = text.lower()
        assert "borderline" not in low, f"{name} prompt contains borderline"
        assert "key" not in low, f"{name} prompt contains key"

    plow = plain.lower()
    for banned in ["danger", "resource", "decision point"]:
        assert banned not in plow, f"plain prompt contains {banned}"
    for num in [str(DANGER_HR), str(DANGER_RR), str(DANGER_SPO2), str(SEVERE_PAIN_THRESHOLD)]:
        # Pain score 7 is a threshold value we must not expose in the plain prompt.
        # The note text is appended by build_prompt; strip the note before checking.
        plain_only = plain.split("Patient note:")[0]
        assert num not in plain_only, f"plain prompt contains threshold {num}"

    rlow = rules
    for req in [str(DANGER_HR), str(DANGER_RR), str(DANGER_SPO2), str(SEVERE_PAIN_THRESHOLD)]:
        assert req in rlow, f"rules prompt missing {req}"


if __name__ == "__main__":
    validate_prompts()
    # Load the first dev public record and print both prompts.
    dev_pub = _HERE / "data" / "dev_public.jsonl"
    with dev_pub.open("r", encoding="utf-8") as f:
        first = json.loads(f.readline())
    print("=== RULES PROMPT ===")
    print(build_prompt(first["note"], "rules"))
    print()
    print("=== PLAIN PROMPT ===")
    print(build_prompt(first["note"], "plain"))
