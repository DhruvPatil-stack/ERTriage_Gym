# ESI Benchmark Evaluation Harness

This folder holds the harness for the ESI triage benchmark.
It builds the data, scores models, and writes reports.

## Layout

- `eval_config.py` holds all tuning constants.
- `build_dataset.py` builds the dev and test splits.
- `prompts.py` builds the two prompt forms: rules and plain.
- `parse.py` turns a model response into an ESI level.
- `metrics.py` computes accuracy, kappa, undertriage, and more.
- `adapters.py` holds the base adapter and the mocks.
- `adapters_ollama.py` holds the Ollama HTTP adapter.
- `run_eval.py` runs one adapter over one split.
- `run_all.py` runs every planned entry from `reports/run_plan.txt`.
- `compare.py` runs a paired bootstrap and an exact McNemar test.
- `review_sheet.py` writes CSV files for manual review.
- `export_batches.py` writes batch files for manual review.
- `import_responses.py` reads manual answers into a run.
- `analyze.py` lists suspect keys from the test runs.
- `test_harness.py` runs the 23 self-tests.

## Data files

- `data/dev_public.jsonl` holds 78 dev items. Each line has `id` and `note`.
- `data/dev_key.jsonl` holds the dev keys. Keys stay out of model prompts.
- `data/test_public.jsonl` holds 208 test items.
- `data/test_key.jsonl` holds the test keys.
- `data/manifest.json` holds hashes and counts for every file.

## Run order

1. Run `py eval/test_harness.py`. Every test must pass.
2. Run `py eval/detect_hardware.py`.
3. Run `py eval/setup_models.py` to pull Ollama models.
4. Run `py eval/smoke_test.py` to measure latency.
5. Run `py eval/make_run_plan.py` to build the run plan.
6. Run `py eval/run_all.py` to score every model.
7. Run `py eval/analyze.py` for suspect keys.
8. Run `py eval/run_comparisons.py` for pairwise checks.
9. Run `py eval/make_summary.py` to write `step4_summary.md`.
10. Run `py eval/security_check.py`.
11. Run `py eval/checksums_after.py`.

## Hard rules (Section 10 limits)

- The dataset seed is `2026`. The build seed is fixed.
- Dev holds 78 items. Test holds 208 items.
- Each variant appears 3 times in dev and 8 times in test.
- Borderline count: 6 in dev, 24 in test.
- The key file never ships inside any prompt.
- The `plain` prompt hides the words `danger`, `resource`, and `decision point`.
- The `plain` prompt hides the threshold numbers 100, 20, 92, and 7.
- The `rules` prompt lists all four thresholds.
- Benchmarks use only one local server. The URL is `http://localhost:11434`.
- No run makes any other network call.
- The run time budget is 3 hours. Items in excess get dropped from the end.
- The download budget is 15 GB total.
- A model takes at most half of free RAM.
- Each model must fit the parse error limit of 10 percent on the smoke run.
- Prompt version `p1` is the default. Prompt `p2` adds a strict JSON tail.
- Bootstrap uses 2000 resamples and seed `7`.
- All random draws use numpy `default_rng` with a fixed seed.

## Metric notes

- Accuracy counts non-ok items as wrong.
- Accuracy_excl_errors counts only ok items.
- Undertriage and overtriage apply to ok items only.
- Critical undertriage counts cases where key is 1 or 2 and answer is 3 or above.
- Kappa uses quadratic weights across the 5 classes.
- The effective key uses the nearest acceptable level. Ties go lower.

## Mock adapters

- `oracle`: returns the correct level.
- `always3`: returns level 3.
- `random`: returns a uniform level 1 to 5.
- `noisy_oracle_p02`: correct with probability 0.8.
- `under_by_one`: returns the correct level plus one, capped at 5.
- `over_by_one`: returns the correct level minus one, floored at 1.
- `garbage`: returns a non-JSON string.
- `fenced`: returns the correct level in a markdown fence.
- `string_level`: returns the correct level as a string.
- `condition_best`: returns the most common dev level per condition.

## Restart behavior

- The runner reads any existing `responses.jsonl`.
- It skips every id already in that file.
- Each new record goes to disk at once.
- A crashed run can resume with the same run id.

## Test split access control

- The runner requires `--allow-test` for the test split.
- Every test run gets a line in `runs/test_access_log.jsonl`.
- A warning prints on repeat use of adapter plus prompt.
