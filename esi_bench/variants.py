"""
26 clinical variants. Each variant fixes needs_immediate, high_risk, and resource_count.
Vital sign ranges keep the required margin from the danger zone limits (design rule D4).
All weights, ranges, and resource lists are provisional. Mark each with VERIFY.
"""
from config import STABLE_HR, STABLE_RR, STABLE_SPO2

# Stable vital ranges used by most variants - VERIFY
_S_HR  = STABLE_HR   # (62, 90) bpm
_S_RR  = STABLE_RR   # (12, 17) breaths/min
_S_SPO2 = STABLE_SPO2  # (96, 100) %

VARIANTS = [
    # ── ESI 1 ──────────────────────────────────────────────────────────────────
    {
        "variant_id":          "V01",
        "condition_name":      "cardiac_arrest",
        "intended_esi":        1,
        "weight":              0.010,   # VERIFY
        "is_borderline_variant": False,
        "needs_immediate":     True,
        "high_risk":           False,
        "resource_count":      3,       # VERIFY
        "age_range":           (18, 90),
        "mental_choices":      [("unresponsive", 1.00)],
        "pain_range":          (0, 0),
        "hr_range":            None,    # vital signs not obtainable
        "rr_range":            None,
        "spo2_range":          None,
        "complaints":          [
            "found unresponsive",
            "found collapsed and unresponsive",
        ],
        "findings":            [
            "No pulse and no breathing on exam.",
            "Bystanders report sudden collapse. No pulse found.",
        ],
    },
    {
        "variant_id":          "V02",
        "condition_name":      "severe_breathing",
        "intended_esi":        1,
        "weight":              0.010,   # VERIFY
        "is_borderline_variant": False,
        "needs_immediate":     True,
        "high_risk":           False,
        "resource_count":      3,       # VERIFY
        "age_range":           (18, 90),
        "mental_choices":      [("lethargic", 1.00)],
        "pain_range":          (0, 5),
        "hr_range":            (120, 150),  # clearly in danger zone: 120-100=20 >= MARGIN_HR=8 - VERIFY
        "rr_range":            (30, 40),    # 30-20=10 >= MARGIN_RR=3 - VERIFY
        "spo2_range":          (70, 82),    # 92-82=10 >= MARGIN_SPO2=3 - VERIFY
        "complaints":          [
            "extreme difficulty breathing",
            "cannot breathe at all",
        ],
        "findings":            [
            "Patient is gasping and lips are blue. Cannot speak.",
            "Cyanotic lips and gasping respirations. Cannot follow commands.",
        ],
    },
    # ── ESI 2 ──────────────────────────────────────────────────────────────────
    {
        "variant_id":          "V03",
        "condition_name":      "severe_breathing",
        "intended_esi":        2,
        "weight":              0.015,   # VERIFY
        "is_borderline_variant": False,
        "needs_immediate":     False,
        "high_risk":           True,    # speaks only 2-3 words -> high-risk per ESI point B
        "resource_count":      3,       # VERIFY
        "age_range":           (18, 90),
        "mental_choices":      [("anxious", 1.00)],
        "pain_range":          (0, 5),
        "hr_range":            (108, 130),  # 108-100=8 >= MARGIN_HR - VERIFY
        "rr_range":            (24, 32),    # 24-20=4 >= MARGIN_RR - VERIFY
        "spo2_range":          (84, 89),    # 92-89=3 >= MARGIN_SPO2 - VERIFY
        "complaints":          [
            "severe shortness of breath",
            "very hard to breathe",
        ],
        "findings":            [
            "Speaks only 2 to 3 words at a time. Uses neck muscles to breathe.",
            "Accessory neck muscle use. Maximum 3 words per breath.",
        ],
    },
    {
        "variant_id":          "V05",
        "condition_name":      "chest_pain",
        "intended_esi":        2,
        "weight":              0.030,   # VERIFY
        "is_borderline_variant": False,
        "needs_immediate":     False,
        "high_risk":           True,    # pressure with radiation and diaphoresis -> high risk
        "resource_count":      3,       # VERIFY: ECG, troponin, chest X-ray
        "age_range":           (30, 90),
        "mental_choices":      [("anxious", 1.00)],
        "pain_range":          (3, 5),  # pain not used to decide level; kept <= 5 per D5
        "hr_range":            _S_HR,
        "rr_range":            _S_RR,
        "spo2_range":          _S_SPO2,
        "complaints":          [
            "pressure in the chest",
            "crushing chest pressure",
        ],
        "findings":            [
            "Pain spreads to the left arm. Patient is sweating. Pressure-type chest pain.",
            "Diaphoresis present. Left arm radiation. Describes crushing chest pressure.",
        ],
    },
    {
        "variant_id":          "V08",
        "condition_name":      "stroke_signs",
        "intended_esi":        2,
        "weight":              0.030,   # VERIFY
        "is_borderline_variant": False,
        "needs_immediate":     False,
        "high_risk":           True,    # FAST-positive presentation -> high risk
        "resource_count":      3,       # VERIFY: CT head, labs, neurology consult
        "age_range":           (40, 90),
        "mental_choices":      [
            ("alert",   0.60),
            ("anxious", 0.40),
        ],
        "pain_range":          (0, 3),
        "hr_range":            _S_HR,
        "rr_range":            _S_RR,
        "spo2_range":          _S_SPO2,
        "complaints":          [
            "sudden face droop and arm weakness",
            "sudden weakness on one side",
        ],
        "findings":            [
            "Left face droop, left arm weakness, and slurred speech. Onset 1 hour ago.",
            "Facial asymmetry on the left side. Slurred speech. Left arm drifts down.",
        ],
    },
    {
        "variant_id":          "V10",
        "condition_name":      "infection_tachycardia",
        "intended_esi":        2,
        "weight":              0.025,   # VERIFY
        "is_borderline_variant": False,
        "needs_immediate":     False,
        "high_risk":           False,
        "resource_count":      3,       # VERIFY: blood cultures, IV antibiotics, labs
        "age_range":           (18, 90),
        "mental_choices":      [("confused", 1.00)],  # confused triggers ESI 2 at point B
        "pain_range":          (0, 5),
        "hr_range":            (115, 135),  # 115-100=15 >= MARGIN_HR - VERIFY
        "rr_range":            (23, 28),    # 23-20=3 >= MARGIN_RR - VERIFY
        "spo2_range":          (95, 98),    # stable on SpO2, danger via HR and RR - VERIFY
        "complaints":          [
            "fever with new confusion",
            "high fever and sudden confusion",
        ],
        "findings":            [
            "Fever, shaking chills, and new onset confusion noted by family today.",
            "Rigors. Family reports sudden change in behaviour. High fever.",
        ],
    },
    {
        "variant_id":          "V11",
        "condition_name":      "infection_tachycardia",
        "intended_esi":        2,
        "weight":              0.025,   # VERIFY
        "is_borderline_variant": False,
        "needs_immediate":     False,
        "high_risk":           False,
        "resource_count":      2,       # VERIFY: blood tests, IV fluids
        "age_range":           (18, 90),
        "mental_choices":      [("alert", 1.00)],  # ESI 2 comes from HR danger zone at D
        "pain_range":          (0, 5),
        "hr_range":            (108, 120),  # 108-100=8 >= MARGIN_HR; all values above 100 - VERIFY
        "rr_range":            (14, 17),    # stable RR - VERIFY
        "spo2_range":          (96, 99),    # stable SpO2 - VERIFY
        "complaints":          [
            "fever for 3 days with body aches",
            "3-day fever and weakness",
        ],
        "findings":            [
            "Fever for 3 days. Body aches. Alert and oriented to person, place, and time.",
            "Three-day fever with myalgia. Drinks fluids. Alert and oriented.",
        ],
    },
    {
        "variant_id":          "V13",
        "condition_name":      "abdominal_pain",
        "intended_esi":        2,
        "weight":              0.040,   # VERIFY
        "is_borderline_variant": False,
        "needs_immediate":     False,
        "high_risk":           False,
        "resource_count":      3,       # VERIFY: labs, CT abdomen, IV fluids
        "age_range":           (18, 90),
        "mental_choices":      [("alert", 1.00)],
        "pain_range":          (9, 10),  # severe pain >= 7 triggers ESI 2 at point B per D5
        "hr_range":            _S_HR,
        "rr_range":            _S_RR,
        "spo2_range":          _S_SPO2,
        "complaints":          [
            "severe low right belly pain with fever",
            "right lower abdomen pain that moved from the navel",
        ],
        "findings":            [
            "Pain started at the navel and moved to the lower right. Guarding on exam. Low fever.",
            "Right lower quadrant pain with migration from umbilicus. Abdominal guarding. Fever.",
        ],
    },
    {
        "variant_id":          "V16",
        "condition_name":      "broken_arm",
        "intended_esi":        2,
        "weight":              0.025,   # VERIFY
        "is_borderline_variant": False,
        "needs_immediate":     False,
        "high_risk":           False,
        "resource_count":      3,       # VERIFY: X-ray, ortho consult, IV pain medicine
        "age_range":           (18, 90),
        "mental_choices":      [("anxious", 1.00)],
        "pain_range":          (9, 10),  # severe pain >= 7 triggers ESI 2 at point B per D5
        "hr_range":            _S_HR,
        "rr_range":            _S_RR,
        "spo2_range":          _S_SPO2,
        "complaints":          [
            "arm bent at wrong angle after a fall",
            "arm deformity with pale and cold hand",
        ],
        "findings":            [
            "Arm bent at abnormal angle. Hand is pale and cold. Fingers do not move.",
            "Obvious deformity. Pale and cool hand below the injury. No finger movement.",
        ],
    },
    {
        "variant_id":          "V21",
        "condition_name":      "sore_throat",
        "intended_esi":        2,
        "weight":              0.020,   # VERIFY
        "is_borderline_variant": False,
        "needs_immediate":     False,
        "high_risk":           True,    # drooling and muffled voice suggest peritonsillar or epiglottitis
        "resource_count":      2,       # VERIFY: ENT consult, labs
        "age_range":           (18, 90),
        "mental_choices":      [("anxious", 1.00)],
        "pain_range":          (3, 5),
        "hr_range":            _S_HR,
        "rr_range":            _S_RR,
        "spo2_range":          _S_SPO2,
        "complaints":          [
            "severe sore throat with drooling",
            "cannot swallow and is drooling",
        ],
        "findings":            [
            "Severe sore throat. Drooling. Muffled voice. Cannot swallow saliva.",
            "Hot-potato voice. Drooling present. Refuses to swallow.",
        ],
    },
    {
        "variant_id":          "V24",
        "condition_name":      "skin_rash",
        "intended_esi":        2,
        "weight":              0.020,   # VERIFY
        "is_borderline_variant": False,
        "needs_immediate":     False,
        "high_risk":           True,    # wheeze after new medicine suggests anaphylaxis
        "resource_count":      2,       # VERIFY: IV epinephrine, monitoring
        "age_range":           (18, 90),
        "mental_choices":      [("anxious", 1.00)],
        "pain_range":          (2, 4),
        "hr_range":            _S_HR,
        "rr_range":            _S_RR,
        "spo2_range":          _S_SPO2,
        "complaints":          [
            "itchy rash and swollen lips after a new medicine",
            "allergic reaction after taking a new medicine",
        ],
        "findings":            [
            "Itchy rash over the chest. Swollen lips. Wheeze heard on exam. New medicine taken 1 hour ago.",
            "Urticarial rash. Lip swelling. Audible wheeze. New medicine 1 hour ago.",
        ],
    },
    # ── ESI 3 ──────────────────────────────────────────────────────────────────
    {
        "variant_id":          "V04",
        "condition_name":      "severe_breathing",
        "intended_esi":        3,
        "weight":              0.055,   # VERIFY
        "is_borderline_variant": True,  # borderline: stable vitals, nudge may trigger danger zone
        "needs_immediate":     False,
        "high_risk":           False,
        "resource_count":      2,       # VERIFY: nebulized medicine, chest X-ray
        "age_range":           (18, 90),
        "mental_choices":      [("anxious", 0.60), ("alert", 0.40)],
        "pain_range":          (0, 5),
        "hr_range":            _S_HR,
        "rr_range":            _S_RR,
        "spo2_range":          _S_SPO2,
        "complaints":          [
            "shortness of breath with known asthma",
            "asthma flare-up",
        ],
        "findings":            [
            "Audible wheeze. Speaks in full sentences. Known asthma. Has inhaler at home.",
            "Wheeze on exam. Full sentences. Known asthma history.",
        ],
    },
    {
        "variant_id":          "V06",
        "condition_name":      "chest_pain",
        "intended_esi":        3,
        "weight":              0.070,   # VERIFY
        "is_borderline_variant": True,
        "needs_immediate":     False,
        "high_risk":           False,
        "resource_count":      2,       # VERIFY: ECG, blood tests
        "age_range":           (18, 90),
        "mental_choices":      [("alert", 1.00)],
        "pain_range":          (3, 5),
        "hr_range":            _S_HR,
        "rr_range":            _S_RR,
        "spo2_range":          _S_SPO2,
        "complaints":          [
            "sharp chest pain",
            "chest pain, sharp and localized",
        ],
        "findings":            [
            "Sharp pain that worsens when the chest wall is pressed. No sweating. No radiation.",
            "Reproducible on chest wall palpation. No diaphoresis. No arm radiation.",
        ],
    },
    {
        "variant_id":          "V09",
        "condition_name":      "stroke_signs",
        "intended_esi":        3,
        "weight":              0.055,   # VERIFY
        "is_borderline_variant": True,
        "needs_immediate":     False,
        "high_risk":           False,
        "resource_count":      2,       # VERIFY: blood tests, ECG
        "age_range":           (40, 90),
        "mental_choices":      [("alert", 1.00)],
        "pain_range":          (0, 3),
        "hr_range":            _S_HR,
        "rr_range":            _S_RR,
        "spo2_range":          _S_SPO2,
        "complaints":          [
            "dizziness when standing for 2 days",
            "lightheaded on standing",
        ],
        "findings":            [
            "Dizzy when standing for 2 days. No arm weakness. Speech is normal.",
            "Postural dizziness. No focal neurological deficit. Normal speech.",
        ],
    },
    {
        "variant_id":          "V14",
        "condition_name":      "abdominal_pain",
        "intended_esi":        3,
        "weight":              0.085,   # VERIFY
        "is_borderline_variant": True,
        "needs_immediate":     False,
        "high_risk":           False,
        "resource_count":      2,       # VERIFY: blood tests, CT abdomen
        "age_range":           (18, 90),
        "mental_choices":      [("alert", 1.00)],
        "pain_range":          (4, 5),  # pain <= 5 per D5 to avoid B trigger
        "hr_range":            _S_HR,
        "rr_range":            _S_RR,
        "spo2_range":          _S_SPO2,
        "complaints":          [
            "diffuse belly pain with vomiting",
            "stomach pain and vomiting",
        ],
        "findings":            [
            "Diffuse belly pain. Vomited twice today. Still able to drink fluids.",
            "Generalised abdominal pain. Two episodes of vomiting. Tolerates oral fluids.",
        ],
    },
    {
        "variant_id":          "V17",
        "condition_name":      "broken_arm",
        "intended_esi":        3,
        "weight":              0.070,   # VERIFY
        "is_borderline_variant": True,
        "needs_immediate":     False,
        "high_risk":           False,
        "resource_count":      2,       # VERIFY: X-ray, orthopaedic consult
        "age_range":           (18, 90),
        "mental_choices":      [("alert", 1.00)],
        "pain_range":          (4, 5),
        "hr_range":            _S_HR,
        "rr_range":            _S_RR,
        "spo2_range":          _S_SPO2,
        "complaints":          [
            "arm deformity after a fall",
            "broken-looking arm after a fall",
        ],
        "findings":            [
            "Visible arm deformity. Fingers move on command. Needs bone specialist.",
            "Deformity at mid-arm. Neurovascular intact distally. Needs orthopaedic evaluation.",
        ],
    },
    {
        "variant_id":          "V25",
        "condition_name":      "skin_rash",
        "intended_esi":        3,
        "weight":              0.055,   # VERIFY
        "is_borderline_variant": True,
        "needs_immediate":     False,
        "high_risk":           False,
        "resource_count":      2,       # VERIFY: blood tests, IV antibiotics
        "age_range":           (18, 90),
        "mental_choices":      [("alert", 1.00)],
        "pain_range":          (3, 5),
        "hr_range":            _S_HR,
        "rr_range":            _S_RR,
        "spo2_range":          _S_SPO2,
        "complaints":          [
            "red spreading skin on the leg with fever",
            "warm red skin on the lower leg",
        ],
        "findings":            [
            "Red, warm, and tender skin on the lower leg. Fever. Area is expanding.",
            "Expanding erythema on lower leg. Tender and warm to touch. Fever present.",
        ],
    },
    # ── ESI 4 ──────────────────────────────────────────────────────────────────
    {
        "variant_id":          "V07",
        "condition_name":      "chest_pain",
        "intended_esi":        4,
        "weight":              0.050,   # VERIFY
        "is_borderline_variant": False,
        "needs_immediate":     False,
        "high_risk":           False,
        "resource_count":      1,       # VERIFY: ECG only
        "age_range":           (18, 90),
        "mental_choices":      [("alert", 1.00)],
        "pain_range":          (2, 4),
        "hr_range":            _S_HR,
        "rr_range":            _S_RR,
        "spo2_range":          _S_SPO2,
        "complaints":          [
            "sore chest after lifting heavy boxes",
            "chest soreness from exertion",
        ],
        "findings":            [
            "Sore chest after lifting heavy boxes today. Pain worsens with arm movement.",
            "Musculoskeletal chest pain after exertion. Worsens on arm movement.",
        ],
    },
    {
        "variant_id":          "V12",
        "condition_name":      "infection_tachycardia",
        "intended_esi":        4,
        "weight":              0.050,   # VERIFY
        "is_borderline_variant": False,
        "needs_immediate":     False,
        "high_risk":           False,
        "resource_count":      1,       # VERIFY: urine test
        "age_range":           (18, 90),
        "mental_choices":      [("alert", 1.00)],
        "pain_range":          (2, 4),
        "hr_range":            _S_HR,
        "rr_range":            _S_RR,
        "spo2_range":          _S_SPO2,
        "complaints":          [
            "burning with urination for 2 days",
            "painful urination for 2 days",
        ],
        "findings":            [
            "Burning urination for 2 days. No fever. No back pain.",
            "Dysuria for 2 days. Afebrile. Denies flank pain.",
        ],
    },
    {
        "variant_id":          "V15",
        "condition_name":      "abdominal_pain",
        "intended_esi":        4,
        "weight":              0.060,   # VERIFY
        "is_borderline_variant": False,
        "needs_immediate":     False,
        "high_risk":           False,
        "resource_count":      1,       # VERIFY: blood tests
        "age_range":           (18, 90),
        "mental_choices":      [("alert", 1.00)],
        "pain_range":          (1, 3),
        "hr_range":            _S_HR,
        "rr_range":            _S_RR,
        "spo2_range":          _S_SPO2,
        "complaints":          [
            "mild cramps after meals",
            "stomach cramps after eating",
        ],
        "findings":            [
            "Mild cramps after meals for 3 days. No vomiting. Normal stool.",
            "Post-meal cramps for 3 days. No nausea or vomiting. Bowel movements normal.",
        ],
    },
    {
        "variant_id":          "V18",
        "condition_name":      "broken_arm",
        "intended_esi":        4,
        "weight":              0.045,   # VERIFY
        "is_borderline_variant": False,
        "needs_immediate":     False,
        "high_risk":           False,
        "resource_count":      1,       # VERIFY: X-ray
        "age_range":           (18, 90),
        "mental_choices":      [("alert", 1.00)],
        "pain_range":          (2, 4),
        "hr_range":            _S_HR,
        "rr_range":            _S_RR,
        "spo2_range":          _S_SPO2,
        "complaints":          [
            "wrist pain and swelling after a fall",
            "wrist pain after falling on an outstretched hand",
        ],
        "findings":            [
            "Wrist pain and mild swelling after a fall. Fingers move normally. No obvious deformity.",
            "Tender wrist with swelling. Full finger movement present. No deformity.",
        ],
    },
    {
        "variant_id":          "V19",
        "condition_name":      "ankle_sprain",
        "intended_esi":        4,
        "weight":              0.045,   # VERIFY
        "is_borderline_variant": False,
        "needs_immediate":     False,
        "high_risk":           False,
        "resource_count":      1,       # VERIFY: X-ray
        "age_range":           (18, 90),
        "mental_choices":      [("alert", 1.00)],
        "pain_range":          (3, 5),
        "hr_range":            _S_HR,
        "rr_range":            _S_RR,
        "spo2_range":          _S_SPO2,
        "complaints":          [
            "twisted ankle, swollen and painful",
            "ankle pain after a twisting injury",
        ],
        "findings":            [
            "Twisted ankle. Ankle is swollen. Cannot bear weight on the foot.",
            "Ankle sprain with visible swelling. Unable to put weight on the foot.",
        ],
    },
    # ── ESI 5 ──────────────────────────────────────────────────────────────────
    {
        "variant_id":          "V20",
        "condition_name":      "ankle_sprain",
        "intended_esi":        5,
        "weight":              0.028,   # VERIFY
        "is_borderline_variant": False,
        "needs_immediate":     False,
        "high_risk":           False,
        "resource_count":      0,
        "age_range":           (18, 90),
        "mental_choices":      [("alert", 1.00)],
        "pain_range":          (1, 3),
        "hr_range":            _S_HR,
        "rr_range":            _S_RR,
        "spo2_range":          _S_SPO2,
        "complaints":          [
            "twisted ankle yesterday, walking today",
            "mild ankle pain after yesterday's twist",
        ],
        "findings":            [
            "Ankle twisted yesterday. Walks with a mild limp. Mild swelling only.",
            "Yesterday's ankle twist. Ambulatory with a slight limp. Minor swelling.",
        ],
    },
    {
        "variant_id":          "V22",
        "condition_name":      "sore_throat",
        "intended_esi":        5,
        "weight":              0.027,   # VERIFY
        "is_borderline_variant": False,
        "needs_immediate":     False,
        "high_risk":           False,
        "resource_count":      0,
        "age_range":           (18, 90),
        "mental_choices":      [("alert", 1.00)],
        "pain_range":          (1, 3),
        "hr_range":            _S_HR,
        "rr_range":            _S_RR,
        "spo2_range":          _S_SPO2,
        "complaints":          [
            "sore throat for 2 days",
            "mild sore throat, no fever",
        ],
        "findings":            [
            "Sore throat for 2 days. No fever. Swallows normally.",
            "Two-day pharyngitis. Afebrile. No difficulty swallowing.",
        ],
    },
    {
        "variant_id":          "V23",
        "condition_name":      "sore_throat",
        "intended_esi":        5,
        "weight":              0.027,   # VERIFY
        "is_borderline_variant": False,
        "needs_immediate":     False,
        "high_risk":           False,
        "resource_count":      0,       # VERIFY: point-of-care swab does not count as a resource per ESI
        "age_range":           (18, 90),
        "mental_choices":      [("alert", 1.00)],
        "pain_range":          (2, 4),
        "hr_range":            _S_HR,
        "rr_range":            _S_RR,
        "spo2_range":          _S_SPO2,
        "complaints":          [
            "sore throat with fever for 3 days",
            "sore throat and white patches in mouth",
        ],
        "findings":            [
            "Sore throat for 3 days. Fever. White patches visible in the throat. Swallows with some pain.",
            "Three-day sore throat. Low fever. Exudate on tonsils. Painful but able to swallow.",
        ],
    },
    {
        "variant_id":          "V26",
        "condition_name":      "skin_rash",
        "intended_esi":        5,
        "weight":              0.028,   # VERIFY
        "is_borderline_variant": False,
        "needs_immediate":     False,
        "high_risk":           False,
        "resource_count":      0,
        "age_range":           (18, 90),
        "mental_choices":      [("alert", 1.00)],
        "pain_range":          (0, 3),
        "hr_range":            _S_HR,
        "rr_range":            _S_RR,
        "spo2_range":          _S_SPO2,
        "complaints":          [
            "itchy patches on both arms for 1 week",
            "arm rash for 1 week",
        ],
        "findings":            [
            "Itchy patches on both arms for 1 week. No fever. No other symptoms.",
            "One-week bilateral arm rash. No systemic symptoms. No fever.",
        ],
    },
]

# Runtime validation: weights must sum to 1.0
_total = sum(v["weight"] for v in VARIANTS)
assert abs(_total - 1.0) < 1e-9, f"Variant weights sum to {_total:.6f}, not 1.0"

# Index by variant_id for fast lookup
VARIANT_BY_ID = {v["variant_id"]: v for v in VARIANTS}

# Sorted list of weights for sampling
_VARIANT_WEIGHTS = [v["weight"] for v in VARIANTS]
