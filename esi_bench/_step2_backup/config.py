# All thresholds come from the ESI Implementation Handbook, 5th edition. VERIFY each one.

# ESI danger zone thresholds for adults
DANGER_HR   = 100   # heart rate above this value is danger zone - VERIFY
DANGER_RR   = 20    # respiratory rate above this value is danger zone - VERIFY
DANGER_SPO2 = 92    # SpO2 below this value is danger zone - VERIFY

# Pain score that triggers ESI 2 at decision point B
SEVERE_PAIN_THRESHOLD = 8  # VERIFY (handbook uses "severe pain or distress")

# Vital sign clip ranges to remove physiologically impossible values
HR_CLIP   = (30, 220)  # bpm - VERIFY
RR_CLIP   = (6, 50)    # breaths per minute - VERIFY
SPO2_CLIP = (60, 100)  # percent - VERIFY
PAIN_CLIP = (0, 10)

# Adult age range
AGE_RANGE = (18, 90)

# Fraction of patients at decision point D that receive a borderline vital sign nudge
BORDERLINE_FRACTION = 0.15  # lowered from 0.4: 0.4 pushed too many D patients into danger zone - VERIFY

# Target ESI distribution - provisional guess, NOT verified against real ED data - VERIFY
TARGET_MIX = {1: 0.02, 2: 0.20, 3: 0.40, 4: 0.28, 5: 0.10}

# Fixed seed for reproducibility
SEED = 42
