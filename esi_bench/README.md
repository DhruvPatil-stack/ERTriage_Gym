# ESI Bench — Step 2.5

## Purpose

This folder is a synthetic benchmark for the Emergency Severity Index (ESI).
ESI is a 5-level triage scale. Level 1 is most critical. Level 5 is least critical.
The benchmark generates adult patients from a variant table.
A rule-based labeler assigns each patient an ESI level and a set of acceptable levels.
Later steps will send text notes to language models and compare their answers to the labeler.

---

## Files

| File | Purpose |
|---|---|
| `config.py` | All numeric constants. Each unverified number has a VERIFY comment. |
| `conditions.py` | Step 2 condition table. Kept for reference. Not used by the generator. |
| `variants.py` | 26 clinical variants. Each variant fixes all hidden values. |
| `labeler.py` | ESI rule engine. Applies 4 decision points. Exports `is_correct`. |
| `generator.py` | Generates one patient per call from the variant table. |
| `test_labeler.py` | 59 unit tests. Covers decision points, boundaries, variants, and leak. |
| `check_distribution.py` | Generates 10,000 patients. Reports ESI shares and variant counts. |
| `ceiling.py` | Computes the Bayes ceiling and 3 baselines for any generator. |
| `reports/ceiling_v1.txt` | Ceiling for the Step 2 (old) generator: 74.11%. |
| `reports/ceiling_v2.txt` | Ceiling for the Step 2.5 (new) generator: 100.00%. |
| `_step2_backup/` | Backup of all Step 2 files before any Step 2.5 changes. |

---

## The Bayes Ceiling

The Bayes ceiling is the highest accuracy any system can reach using only the visible note.
When 2 patients have the same note but different correct labels, no system can be correct for both.

The Step 2 generator drew needs_immediate, high_risk, and resource_count at random.
Two patients with the same note could get different correct labels because the hidden draws differed.
This set the ceiling at 74.11% before any model saw any data.

The Step 2.5 variants fix the hidden values. The note now determines the label.
The new ceiling is 100.00% for all patients (including borderline cases, which accept 2 levels).
A model that reads notes correctly can now achieve close to 100%.

---

## The Variant System

Each variant defines one clinical picture inside a condition. For example:
- V13 is "severe abdominal pain with guarding" (ESI 2 via severe pain).
- V14 is "diffuse abdominal pain with vomiting" (ESI 3, borderline).
- V15 is "mild post-meal cramps" (ESI 4).

Each variant fixes needs_immediate, high_risk, and resource_count. These do not change across patients.
The generator draws age, sex, pain score, mental status, vital signs, and note phrasing from the variant.

---

## Borderline Cases

Borderline variants are V04, V06, V09, V14, V17, and V25.
Each borderline variant has stable vital signs as its base.
With probability BORDERLINE_FRACTION = 0.15, one vital sign is nudged within BORDERLINE_BAND = 2 units of its limit.
The nudged value can fall on either side of the limit. This may or may not cross into the danger zone.
Borderline patients have acceptable_levels = [2, 3]. Both ESI 2 and ESI 3 are correct answers.

---

## Known Simplifications

**S1: Danger zone is automatic.**
The labeler makes danger zone vital signs trigger ESI 2 at decision point D automatically.
The real ESI handbook says to "consider" ESI 2. Clinical judgment may override the rule. VERIFY.

**S2: Severe pain threshold is a fixed number.**
The labeler triggers ESI 2 at point B when pain score is 7 or above.
The real handbook uses the phrase "severe pain or distress" without a fixed number. VERIFY.
Pain scores of 6 or below do not decide the ESI level. Pain scores of 9 or 10 decide it.
Scores of 7 or 8 are not used in variants per design rule D5.

**S3: High-risk flag is a fixed probability per variant.**
For ESI 2 variants that use high_risk, the flag is always True.
A real triage nurse uses full clinical assessment. The text note carries the clinical evidence.
A language model must infer high risk from the complaint and findings. The note does not say "high risk".

**S4: Vital signs are drawn independently.**
Each vital sign is drawn from a separate uniform distribution within its range.
Real vital signs are correlated. For example, fever raises both heart rate and respiratory rate together.
The generator does not model this correlation. A patient may have a fever-pattern complaint with normal vital signs.
This is accepted as a simplification. VERIFY whether correlation matters for ESI accuracy.

**S5: Adults only.**
All patients are aged 18 to 90. Pediatric vital sign thresholds differ. No children are in this benchmark.

**S6: Point-of-care tests are not resources.**
Variant V23 shows a sore throat with a rapid throat swab.
The ESI handbook lists point-of-care tests as non-resources. V23 has resource_count = 0. VERIFY.

**S7: A high score means the model follows the ESI algorithm.**
It does not mean the model agrees with real triage nurses. Real nurse review is a later phase.

---

## VERIFY Items

| Item | Value used | Source needed |
|---|---|---|
| DANGER_HR | 100 bpm | ESI Implementation Handbook, 5th ed. |
| DANGER_RR | 20 breaths/min | ESI Implementation Handbook, 5th ed. |
| DANGER_SPO2 | 92% | ESI Implementation Handbook, 5th ed. |
| SEVERE_PAIN_THRESHOLD | 7 / 10 | ESI Implementation Handbook, 5th ed. |
| BORDERLINE_FRACTION | 0.15 | No published source. Provisional. |
| BORDERLINE_BAND | 2 units | No published source. Provisional. |
| MARGIN_HR | 8 bpm | Design rule D4. No clinical source. |
| MARGIN_RR | 3 breaths/min | Design rule D4. No clinical source. |
| MARGIN_SPO2 | 3 percent | Design rule D4. No clinical source. |
| STABLE_HR | (62, 90) bpm | Design assumption. Verify against normal ranges. |
| STABLE_RR | (12, 17) breaths/min | Design assumption. Verify against normal ranges. |
| STABLE_SPO2 | (96, 100) percent | Design assumption. Verify against normal ranges. |
| TARGET_MIX | ESI 1=2%, 2=20%, 3=40%, 4=28%, 5=10% | Reference only. Not used. Verify against ED census. |
| All variant weights | See variants.py | Verify against published ED chief complaint data. |
| All resource_count values | See variants.py | Verify against ESI handbook resource definitions. |
| V10 vital ranges | HR 115-135, RR 23-28 | Verify against published sepsis presentations. |
| V11 vital ranges | HR 108-120 | Verify. All values above danger limit by design. |
| Point-of-care tests as non-resources | V23 resource_count=0 | Verify against ESI handbook. |

---

## Resource Definition

The following count as resources (VERIFY against ESI Implementation Handbook):
labs, ECG, X-ray, CT, MRI, ultrasound, IV fluids, IV or IM or nebulized medicine,
specialty consult, simple procedure (1 resource), complex procedure (2 resources).

The following do NOT count (VERIFY):
history and physical exam, point-of-care tests, saline lock, oral medicine,
tetanus shot, prescription refill, simple wound care, crutches, splints, slings.
