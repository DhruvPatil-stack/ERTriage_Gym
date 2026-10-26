# ESI Bench — Step 2

## Purpose

This folder holds a synthetic benchmark for the Emergency Severity Index (ESI).
ESI is a 5-level triage scale. Level 1 is most critical. Level 5 is least critical.
The benchmark generates adult patients from a condition table.
A rule-based labeler assigns each patient an ESI level.
Later steps will send text notes to language models and compare answers to this labeler.

---

## Files

| File | Purpose |
|---|---|
| `config.py` | All numeric constants. Each unverified number has a VERIFY comment. |
| `conditions.py` | The 10 condition definitions. Weights, vital sign distributions, resource weights. |
| `labeler.py` | The ESI rule engine. Applies 4 decision points in order. |
| `generator.py` | Generates one patient per call. Observable fields and hidden fields. |
| `test_labeler.py` | 24 unit tests. One test per decision point and vital sign boundary. |
| `check_distribution.py` | Generates 10,000 patients. Compares ESI shares to target. |

---

## Known Simplifications

**S1: Danger zone is automatic.**
The labeler makes danger zone vital signs trigger ESI 2 automatically.
The real ESI Implementation Handbook says to "consider" ESI 2 for danger zone vitals.
Clinical judgment may override the rule in real triage. VERIFY against handbook.

**S2: Severe pain threshold is a fixed number.**
The labeler triggers ESI 2 at point B when pain score is 8 or above.
The real handbook uses the phrase "severe pain or distress" without a fixed number. VERIFY.

**S3: High-risk flag is a hidden probability.**
The `high_risk` field in each patient is set by a per-condition probability.
A real triage nurse uses full clinical assessment to assign this flag.
The text note does not state "high_risk: true" directly.
A language model must infer risk from the complaint and presentation.

**S4: Vital signs are independent.**
Each vital sign is drawn from a separate normal distribution.
Real vital signs are correlated. For example, fever raises both heart rate and respiratory rate.
The generator does not model this correlation. VERIFY whether correlation matters for ESI accuracy.

**S5: Adults only.**
All patients are aged 18 to 90.
Pediatric vital sign thresholds are different. This benchmark does not cover children.

**S6: Broken arm pain is capped at 7.**
The pain range for broken arm is (4, 7).
Pain of 8 or above triggers ESI 2 at point B.
A severe fracture can produce pain of 8 in a real patient.
The cap prevents the labeler from giving ESI 2 to all high-pain fractures.
This may undertriage a small number of severe fracture cases. VERIFY.

**S7: A high score on this benchmark means the model follows the ESI algorithm.**
It does not mean the model agrees with real triage nurses.
Real nurse review is a later phase.

---

## VERIFY Items

Each item below appears in `config.py` or `conditions.py` with a VERIFY comment.

| Item | Value Used | Source Needed |
|---|---|---|
| DANGER_HR | 100 bpm | ESI Implementation Handbook, 5th ed. |
| DANGER_RR | 20 breaths/min | ESI Implementation Handbook, 5th ed. |
| DANGER_SPO2 | 92% | ESI Implementation Handbook, 5th ed. |
| SEVERE_PAIN_THRESHOLD | 8 / 10 | ESI Implementation Handbook, 5th ed. |
| BORDERLINE_FRACTION | 0.15 | Provisional. No published source. |
| TARGET_MIX | ESI 1=2%, 2=20%, 3=40%, 4=28%, 5=10% | Verify against published ED census data. |
| All condition weights | See conditions.py | Verify against published ED chief complaint data. |
| All p_immediate values | See conditions.py | Verify against published triage literature. |
| All p_high_risk values | See conditions.py | Verify against published triage literature. |
| All vital sign means and SDs | See conditions.py | Verify against published clinical reference ranges. |
| All resource_weights | See conditions.py | Verify against ESI Implementation Handbook resource definitions. |

---

## Resource Definition

The following count as resources (VERIFY against ESI Implementation Handbook):
labs, ECG, X-ray, CT, MRI, ultrasound, IV fluids, IV or IM or nebulized medicine,
specialty consult, simple procedure (1 resource), complex procedure (2 resources).

The following do NOT count (VERIFY):
history and physical exam, point-of-care tests, saline lock, oral medicine,
tetanus shot, prescription refill, simple wound care, crutches, splints, slings.
