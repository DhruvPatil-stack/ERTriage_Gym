"""Evaluation constants.

This file holds all tuning values for the harness. Other modules import these.
It has no logic. Change a value here to adjust the whole run.
"""

DATASET_SEED = 2026
BENCHMARK_VERSION = "0.1"
PROMPT_VERSION = "p1"
BOOTSTRAP_N = 2000
BOOTSTRAP_SEED = 7
FLAG_VARIANT_ACCURACY = 0.5
MAX_DOWNLOAD_GB = 15
MAX_RUN_HOURS = 3
N_MODELS = 3
SMOKE_N = 20
OLLAMA_URL = "http://localhost:11434"
CALL_TIMEOUT_S = 180
CALL_RETRIES = 2
OLLAMA_OPTIONS = {"temperature": 0, "seed": 7, "num_predict": 160, "num_ctx": 4096}
PARSE_ERROR_LIMIT = 0.10
CONSENSUS_SHARE = 0.67
