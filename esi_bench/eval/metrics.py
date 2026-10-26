"""Metric calculations for the ESI benchmark.

This module computes accuracy, kappa, undertriage, and other scores.
It uses only numpy and the standard library.
"""
import math
from collections import defaultdict

import numpy as np


def correct(answer, acceptable_levels):
    """Return True if answer is in acceptable_levels."""
    return int(answer) in acceptable_levels


def effective_key(answer, acceptable_levels):
    """Return answer if correct, else nearest level in acceptable_levels. Ties go lower."""
    if int(answer) in acceptable_levels:
        return int(answer)
    return min(acceptable_levels, key=lambda k: (abs(k - int(answer)), k))


def undertriage(answer, acceptable_levels):
    """Return True if answer rates less urgent than the top of acceptable_levels."""
    return int(answer) > max(acceptable_levels)


def overtriage(answer, acceptable_levels):
    """Return True if answer rates more urgent than the bottom of acceptable_levels."""
    return int(answer) < min(acceptable_levels)


def critical_undertriage(esi_level, answer, acceptable_levels):
    """Return True if key is 1 or 2, answer is wrong, and answer is 3 or higher."""
    if int(esi_level) not in (1, 2):
        return False
    if int(answer) in acceptable_levels:
        return False
    return int(answer) >= 3


def quadratic_weighted_kappa(keys, answers):
    """Return the QWK score for keys and answers.

    The scale has 5 classes (1 to 5). Weights are quadratic.
    Returns 1.0 for perfect agreement.
    """
    if len(keys) == 0:
        return 0.0
    k = np.array([int(x) for x in keys], dtype=int)
    a = np.array([int(x) for x in answers], dtype=int)
    n = len(k)
    classes = 5
    # Build observed matrix. Row = key, col = answer. Index 0 maps to level 1.
    o = np.zeros((classes, classes), dtype=float)
    for i in range(n):
        o[k[i] - 1, a[i] - 1] += 1.0
    # Marginals.
    row_sum = o.sum(axis=1)
    col_sum = o.sum(axis=0)
    # Expected matrix under independence.
    e = np.outer(row_sum, col_sum) / float(n)
    # Weight matrix.
    denom = float((classes - 1) ** 2)
    w = np.zeros((classes, classes), dtype=float)
    for i in range(classes):
        for j in range(classes):
            w[i, j] = ((i - j) ** 2) / denom
    num = float((w * o).sum())
    den = float((w * e).sum())
    if den == 0.0:
        return 1.0
    return 1.0 - num / den


def bootstrap_accuracy_interval(correct_flags, n=2000, seed=7):
    """Return a (lower, upper) 95 percent CI for accuracy by resampling."""
    flags = np.array([1 if x else 0 for x in correct_flags], dtype=int)
    size = len(flags)
    if size == 0:
        return (0.0, 0.0)
    rng = np.random.default_rng(seed)
    means = np.empty(n, dtype=float)
    for i in range(n):
        idx = rng.integers(0, size, size)
        means[i] = flags[idx].mean()
    lower = float(np.percentile(means, 2.5))
    upper = float(np.percentile(means, 97.5))
    return (lower, upper)


def compute_all(responses, keys_dict):
    """Return the full metric set for a run.

    responses: list of dicts with id, level, status.
    keys_dict: dict from id to key record.
    """
    n_total = len(responses)
    correct_flags = []
    non_ok_count = 0
    parse_error = 0
    adapter_error = 0
    missing = 0
    out_of_range = 0

    under_num = 0
    over_num = 0
    under_den = 0
    over_den = 0
    crit_under = 0

    kappa_keys = []
    kappa_answers = []

    confusion = np.zeros((5, 5), dtype=int)

    per_variant = defaultdict(lambda: {"n": 0, "n_correct": 0})
    per_level = defaultdict(lambda: {"n": 0, "n_correct": 0})
    borderline_flags = []
    non_borderline_flags = []

    miss_sizes = defaultdict(int)

    for r in responses:
        rid = r["id"]
        key = keys_dict[rid]
        vid = key["variant_id"]
        key_level = int(key["esi_level"])
        accept = [int(x) for x in key["acceptable_levels"]]
        is_bl = bool(key.get("is_borderline", False))

        status = r.get("status", "parse_error")
        level = r.get("level")

        per_variant[vid]["n"] += 1
        per_level[key_level]["n"] += 1

        if status == "parse_error":
            parse_error += 1
        elif status == "adapter_error":
            adapter_error += 1
        elif status == "missing":
            missing += 1
        elif status == "out_of_range":
            out_of_range += 1

        if status == "ok" and level is not None:
            is_ok_item = True
            ans = int(level)
            is_corr = ans in accept
            correct_flags.append(1 if is_corr else 0)
            if is_corr:
                per_variant[vid]["n_correct"] += 1
                per_level[key_level]["n_correct"] += 1
                miss_sizes[0] += 1
            else:
                eff = effective_key(ans, accept)
                miss = abs(ans - eff)
                miss_sizes[miss] += 1
            # Undertriage and overtriage both count on ok items only.
            if ans > max(accept):
                under_num += 1
            under_den += 1
            if ans < min(accept):
                over_num += 1
            over_den += 1
            if critical_undertriage(key_level, ans, accept):
                crit_under += 1
            # Confusion row = effective key, col = answer.
            eff = effective_key(ans, accept)
            confusion[eff - 1, ans - 1] += 1
            kappa_keys.append(eff)
            kappa_answers.append(ans)
            if is_bl:
                borderline_flags.append(1 if is_corr else 0)
            else:
                non_borderline_flags.append(1 if is_corr else 0)
        else:
            # Non-ok item counts as wrong for accuracy.
            is_ok_item = False
            correct_flags.append(0)
            if is_bl:
                borderline_flags.append(0)
            else:
                non_borderline_flags.append(0)
            non_ok_count += 1

    acc = float(np.mean(correct_flags)) if correct_flags else 0.0
    ci_lower, ci_upper = bootstrap_accuracy_interval(correct_flags)

    # Accuracy excluding errors.
    ok_flags = []
    for r in responses:
        if r.get("status") == "ok" and r.get("level") is not None:
            ans = int(r["level"])
            accept = [int(x) for x in keys_dict[r["id"]]["acceptable_levels"]]
            ok_flags.append(1 if ans in accept else 0)
    acc_excl = float(np.mean(ok_flags)) if ok_flags else 0.0

    kappa = quadratic_weighted_kappa(kappa_keys, kappa_answers) if kappa_keys else 0.0
    under_rate = (under_num / under_den) if under_den else 0.0
    over_rate = (over_num / over_den) if over_den else 0.0

    per_variant_out = {}
    for vid, d in per_variant.items():
        acc_v = (d["n_correct"] / d["n"]) if d["n"] else 0.0
        per_variant_out[vid] = {"n": d["n"], "n_correct": d["n_correct"], "accuracy": acc_v}

    per_level_out = {}
    for lv, d in per_level.items():
        rec = (d["n_correct"] / d["n"]) if d["n"] else 0.0
        per_level_out[lv] = {"n": d["n"], "n_correct": d["n_correct"], "recall": rec}

    bl_acc = float(np.mean(borderline_flags)) if borderline_flags else 0.0
    nbl_acc = float(np.mean(non_borderline_flags)) if non_borderline_flags else 0.0

    return {
        "n_total": n_total,
        "accuracy": acc,
        "accuracy_excl_errors": acc_excl,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "kappa": kappa,
        "undertriage_rate": under_rate,
        "overtriage_rate": over_rate,
        "critical_undertriage_count": crit_under,
        "parse_error_count": parse_error,
        "adapter_error_count": adapter_error,
        "missing_count": missing,
        "out_of_range_count": out_of_range,
        "confusion_matrix": confusion.tolist(),
        "per_variant_accuracy": per_variant_out,
        "per_level_recall": per_level_out,
        "borderline_accuracy": bl_acc,
        "non_borderline_accuracy": nbl_acc,
        "miss_size_distribution": dict(miss_sizes),
    }
