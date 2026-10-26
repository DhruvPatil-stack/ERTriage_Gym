# All thresholds come from the ESI Implementation Handbook, 5th edition. VERIFY each one.

# ESI danger zone thresholds for adults
DANGER_HR   = 100   # heart rate above this value is danger zone - VERIFY
DANGER_RR   = 20    # respiratory rate above this value is danger zone - VERIFY
DANGER_SPO2 = 92    # SpO2 below this value is danger zone - VERIFY

# Pain score that triggers ESI 2 at decision point B
SEVERE_PAIN_THRESHOLD = 7  # VERIFY. Provisional. Handbook says "severe pain or distress".

# Vital sign clip ranges to remove physiologically impossible values
HR_CLIP   = (30, 220)  # bpm - VERIFY
RR_CLIP   = (6, 50)    # breaths per minute - VERIFY
SPO2_CLIP = (60, 100)  # percent - VERIFY
PAIN_CLIP = (0, 10)

# Adult age range
AGE_RANGE = (18, 90)

# Stable vital sign ranges for non-danger variants - VERIFY
STABLE_HR   = (62, 90)   # bpm - VERIFY
STABLE_RR   = (12, 17)   # breaths per minute - VERIFY
STABLE_SPO2 = (96, 100)  # percent - VERIFY

# Minimum distance between a variant vital range and the danger zone limit (design rule D4)
MARGIN_HR   = 8  # bpm - VERIFY
MARGIN_RR   = 3  # breaths per minute - VERIFY
MARGIN_SPO2 = 3  # percent - VERIFY

# Borderline: set 1 vital within this many units of its limit on either side
BORDERLINE_BAND     = 2     # units - VERIFY
BORDERLINE_FRACTION = 0.15  # fraction of borderline-variant patients that receive a nudge - VERIFY

# Target ESI distribution. Reference only. The generator does not tune to this mix.
TARGET_MIX = {1: 0.02, 2: 0.20, 3: 0.40, 4: 0.28, 5: 0.10}  # VERIFY

# Fixed seed for reproducibility
SEED = 42
