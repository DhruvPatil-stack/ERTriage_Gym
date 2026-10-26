import numpy as np

# Each entry is one clinical condition.
# All weights, probabilities, and vital sign parameters are provisional guesses. VERIFY each one.
# mental_status_choices: list of (status_string, probability). Probabilities must sum to 1.0.
# resource_weights: list of 4 floats for P(r=0), P(r=1), P(r=2), P(r=3). Must sum to 1.0.

CONDITIONS = [
    {
        "name":        "cardiac_arrest",
        "weight":      0.01,   # VERIFY - prevalence in ED arrivals
        "typical_esi": 1,
        "complaint":   "unresponsive, no pulse detected",
        "age_range":   (18, 90),
        "p_immediate": 0.97,   # VERIFY - nearly all arrests need immediate intervention
        "p_high_risk": 0.03,   # covers rare cases with return of spontaneous circulation
        "resource_weights": [0.00, 0.00, 0.10, 0.90],  # VERIFY
        "hr_mean": 30,  "hr_sd": 8,    # pulseless bradycardia or asystole
        "rr_mean": 4,   "rr_sd": 2,    # agonal or absent - clips to RR_CLIP minimum
        "spo2_mean": 65, "spo2_sd": 5,
        "pain_range": (0, 0),          # patient is unresponsive
        "mental_status_choices": [("unresponsive", 1.00)],
    },
    {
        "name":        "severe_breathing",
        "weight":      0.03,   # VERIFY
        "typical_esi": 1,
        "complaint":   "severe shortness of breath, speaking in single words",
        "age_range":   (18, 90),
        "p_immediate": 0.10,   # VERIFY - subset needs immediate airway management
        "p_high_risk": 0.70,   # VERIFY - most are high-risk per ESI point B
        "resource_weights": [0.00, 0.05, 0.25, 0.70],  # VERIFY
        "hr_mean": 110, "hr_sd": 20,   # reflex tachycardia from hypoxia
        "rr_mean": 28,  "rr_sd": 5,    # visible respiratory distress
        "spo2_mean": 87, "spo2_sd": 5, # significant hypoxia
        "pain_range": (2, 6),
        "mental_status_choices": [
            ("anxious",   0.40),
            ("alert",     0.30),
            ("confused",  0.20),
            ("lethargic", 0.10),
        ],
    },
    {
        "name":        "chest_pain",
        "weight":      0.06,   # VERIFY
        "typical_esi": 2,
        "complaint":   "chest pressure and diaphoresis",
        "age_range":   (30, 90),
        "p_immediate": 0.01,   # VERIFY
        "p_high_risk": 0.50,   # VERIFY - ACS risk drives high-risk flag
        "resource_weights": [0.00, 0.05, 0.35, 0.60],  # VERIFY
        "hr_mean": 90,  "hr_sd": 20,
        "rr_mean": 18,  "rr_sd": 3,
        "spo2_mean": 97, "spo2_sd": 2,
        "pain_range": (6, 10),  # chest pain is typically severe
        "mental_status_choices": [("alert", 0.70), ("anxious", 0.30)],
    },
    {
        "name":        "stroke_signs",
        "weight":      0.05,   # VERIFY
        "typical_esi": 2,
        "complaint":   "sudden facial droop, arm weakness, and slurred speech",
        "age_range":   (40, 90),
        "p_immediate": 0.03,   # VERIFY
        "p_high_risk": 0.60,   # VERIFY - FAST-positive presentation is high-risk
        "resource_weights": [0.00, 0.05, 0.30, 0.65],  # VERIFY
        "hr_mean": 85,  "hr_sd": 15,
        "rr_mean": 16,  "rr_sd": 3,
        "spo2_mean": 96, "spo2_sd": 2,
        "pain_range": (0, 5),   # headache possible, not severe
        "mental_status_choices": [
            ("confused",  0.45),  # cortical involvement
            ("alert",     0.35),
            ("lethargic", 0.20),
        ],
    },
    {
        "name":        "infection_tachycardia",
        "weight":      0.10,   # VERIFY
        "typical_esi": 2,
        "complaint":   "fever, chills, and body aches with elevated heart rate",
        "age_range":   (18, 90),
        "p_immediate": 0.01,   # VERIFY
        "p_high_risk": 0.10,   # VERIFY - subset meets sepsis high-risk criteria
        "resource_weights": [0.02, 0.05, 0.35, 0.58],  # VERIFY
        "hr_mean": 90,  "hr_sd": 12,  # moderate tachycardia - reduced to lower danger zone rate
        "rr_mean": 16,  "rr_sd": 3,
        "spo2_mean": 97, "spo2_sd": 2,
        "pain_range": (3, 7),
        "mental_status_choices": [
            ("alert",     0.85),
            ("confused",  0.10),
            ("lethargic", 0.05),
        ],
    },
    {
        "name":        "abdominal_pain",
        "weight":      0.32,   # VERIFY - increased to boost ESI 3 share
        "typical_esi": 3,
        "complaint":   "diffuse abdominal pain and nausea",
        "age_range":   (18, 90),
        "p_immediate": 0.005,  # VERIFY - rare surgical abdomen
        "p_high_risk": 0.05,   # VERIFY
        "resource_weights": [0.05, 0.10, 0.55, 0.30],  # VERIFY
        "hr_mean": 80,  "hr_sd": 10,  # near-normal vitals in most cases
        "rr_mean": 16,  "rr_sd": 2,
        "spo2_mean": 98, "spo2_sd": 1,
        "pain_range": (3, 7),   # capped below severe-pain threshold
        "mental_status_choices": [("alert", 0.85), ("anxious", 0.15)],
    },
    {
        "name":        "broken_arm",
        "weight":      0.15,   # VERIFY
        "typical_esi": 3,
        "complaint":   "arm pain and visible deformity after a fall",
        "age_range":   (18, 90),
        "p_immediate": 0.00,
        "p_high_risk": 0.02,   # VERIFY - rare open fracture
        "resource_weights": [0.05, 0.45, 0.45, 0.05],  # VERIFY - mix of ESI 3 and 4
        "hr_mean": 82,  "hr_sd": 12,
        "rr_mean": 16,  "rr_sd": 2,
        "spo2_mean": 99, "spo2_sd": 1,
        "pain_range": (4, 7),   # capped at 7: pain=8 alone triggers ESI 2, which overstates fracture acuity - VERIFY
        "mental_status_choices": [("alert", 0.90), ("anxious", 0.10)],
    },
    {
        "name":        "ankle_sprain",
        "weight":      0.10,   # VERIFY - reduced to bring ESI 4 share down
        "typical_esi": 4,
        "complaint":   "ankle pain and swelling after a twisting injury",
        "age_range":   (18, 90),
        "p_immediate": 0.00,
        "p_high_risk": 0.00,
        "resource_weights": [0.02, 0.93, 0.05, 0.00],  # VERIFY - usually 1 X-ray
        "hr_mean": 78,  "hr_sd": 10,
        "rr_mean": 15,  "rr_sd": 2,
        "spo2_mean": 99, "spo2_sd": 1,
        "pain_range": (2, 6),
        "mental_status_choices": [("alert", 1.00)],
    },
    {
        "name":        "sore_throat",
        "weight":      0.09,   # VERIFY
        "typical_esi": 5,
        "complaint":   "sore throat and difficulty swallowing",
        "age_range":   (18, 90),
        "p_immediate": 0.00,
        "p_high_risk": 0.01,   # VERIFY - rare epiglottitis
        "resource_weights": [0.50, 0.48, 0.02, 0.00],  # VERIFY
        "hr_mean": 76,  "hr_sd": 10,
        "rr_mean": 14,  "rr_sd": 2,
        "spo2_mean": 99, "spo2_sd": 1,
        "pain_range": (1, 5),
        "mental_status_choices": [("alert", 1.00)],
    },
    {
        "name":        "skin_rash",
        "weight":      0.09,   # VERIFY
        "typical_esi": 5,
        "complaint":   "new-onset skin rash over the trunk",
        "age_range":   (18, 90),
        "p_immediate": 0.00,
        "p_high_risk": 0.01,   # VERIFY - rare anaphylaxis
        "resource_weights": [0.50, 0.48, 0.02, 0.00],  # VERIFY
        "hr_mean": 75,  "hr_sd": 10,
        "rr_mean": 14,  "rr_sd": 2,
        "spo2_mean": 99, "spo2_sd": 1,
        "pain_range": (0, 4),
        "mental_status_choices": [("alert", 1.00)],
    },
]

# Runtime validation: weights must sum to 1.0
_total = sum(c["weight"] for c in CONDITIONS)
assert abs(_total - 1.0) < 1e-9, f"Condition weights sum to {_total}, not 1.0"

# Index by name for fast lookup
CONDITION_BY_NAME = {c["name"]: c for c in CONDITIONS}
