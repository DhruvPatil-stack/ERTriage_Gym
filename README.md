# ERTriage_Gym

## What this is

Two components for emergency room triage research:

1. **An RL triage gym.** A Gymnasium environment (`triage_gym.py`) with 5 patient slots, severity 1–5, and wait-time deterioration dynamics. Trained with PPO from Stable-Baselines3 (`train.py`).
2. **A synthetic ESI benchmark** (`esi_bench/`). A variant-based generator produces adult patient notes. A rule-based labeler assigns an Emergency Severity Index level per the 4 ESI decision points. An eval harness (`esi_bench/eval/`) scores language models against the labeler.

## Run

```
pip install -r requirements.txt
python train.py                     # trains PPO for 500,000 timesteps, saves triage_ppo.zip
python evaluate.py                  # compares PPO against a greedy highest-severity baseline over 50 episodes
python esi_bench/test_labeler.py    # runs 59 unit tests on the ESI labeler
```

`requirements.txt` lists `gymnasium` and `numpy`. Training also needs `stable-baselines3`.

## Results

ESI benchmark ceiling (from `esi_bench/reports/ceiling_v2.txt`, N=10,000, seed=42):

- Bayes ceiling (all patients): **100.00%**
- Bayes ceiling (non-borderline, n=9,454): **100.00%**
- Borderline cases: 546
- Visible groups: 35
- Baseline "Always ESI 3": 38.94%
- Baseline "Per-condition best label": 54.99%
- ESI distribution: 1=2.1%, 2=25.8%, 3=36.7%, 4=25.3%, 5=10.1%

Prior generator ceiling (from `esi_bench/reports/ceiling_v1.txt`): **74.11%**.

RL training and PPO-vs-baseline reward numbers are not recorded in this repo. Run `python evaluate.py` to produce them.

## Limits

- **Synthetic data only.** No real patient records are used anywhere.
- **Not a medical device.** This project is not for clinical use.
- **Thresholds marked `VERIFY` are not clinically validated.** See `esi_bench/config.py` and the "VERIFY Items" table in `esi_bench/README.md`.
- **The 100.00% Bayes ceiling is circular.** The Step-2.5 generator fixes `needs_immediate`, `high_risk`, and `resource_count` per variant, and the labeler reads the same fields. The ceiling shows that the labels follow from the variant definitions, not that any model has clinical skill.
- **PPO may not beat the greedy highest-severity baseline.** The repo does not record a measured result; `evaluate.py` is the way to find out.
- **Adults only** (ages 18–90). No pediatric thresholds. See simplification S5 in `esi_bench/README.md`.

## Layout

- `triage_gym.py`, `train.py`, `evaluate.py`, `test_triage.py` — RL environment, PPO training, evaluation, smoke test.
- `triage_ppo.zip` — saved PPO model.
- `esi_bench/` — ESI generator, labeler, ceiling analysis, 26 variants, 59 labeler tests.
- `esi_bench/eval/` — LM evaluation harness: dataset builder, prompts, adapters, metrics, run plan, summary.
- `esi_bench/reports/` — ceiling reports for the old and new generators.
- `esi_bench/_step2_backup/` — snapshot of the Step-2 generator before Step-2.5 changes.
