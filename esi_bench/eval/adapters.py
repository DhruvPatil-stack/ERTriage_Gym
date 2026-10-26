"""Base adapter class and mock adapters.

Each mock extracts the note from the prompt. Oracle and friends look it up.
Mocks never call out to a network.
"""
import json
import os
import re
import sys
from collections import Counter

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


class BaseAdapter:
    """All adapters share this interface."""

    name: str = "base"

    def ask(self, prompt: str) -> str:
        raise NotImplementedError


def _extract_note(prompt: str):
    """Return the note text that follows the 'Patient note:' marker."""
    marker = "Patient note:\n"
    idx = prompt.find(marker)
    if idx == -1:
        return None
    return prompt[idx + len(marker):].strip()


def _build_response(level, reason):
    """Return a JSON string with esi_level and reason."""
    return json.dumps({"esi_level": level, "reason": reason})


def _build_note_index(key_records, note_map):
    """Return a dict from note text to key record."""
    # key_records: list of key dicts with id and other fields.
    # note_map: dict from id to note text.
    out = {}
    for k in key_records:
        rid = k["id"]
        note = note_map.get(rid)
        if note is None:
            continue
        out[note] = k
    return out


class OracleAdapter(BaseAdapter):
    """Return the correct level for every item it finds."""

    name = "oracle"

    def __init__(self, key_records, note_map):
        self.index = _build_note_index(key_records, note_map)

    def ask(self, prompt: str) -> str:
        note = _extract_note(prompt)
        if note is None or note not in self.index:
            return _build_response(3, "oracle fallback")
        k = self.index[note]
        return _build_response(int(k["esi_level"]), "oracle")


class Always3Adapter(BaseAdapter):
    """Return level 3 every time."""

    name = "always3"

    def __init__(self, key_records=None, note_map=None):
        pass

    def ask(self, prompt: str) -> str:
        return _build_response(3, "always 3")


class RandomAdapter(BaseAdapter):
    """Return a uniform random level from 1 to 5."""

    name = "random"

    def __init__(self, key_records=None, note_map=None, seed=42):
        self.rng = np.random.default_rng(seed)

    def ask(self, prompt: str) -> str:
        level = int(self.rng.integers(1, 6))
        return _build_response(level, "random")


class NoisyOracleAdapter(BaseAdapter):
    """Return the correct level most of the time, else a wrong level."""

    name = "noisy_oracle"

    def __init__(self, key_records, note_map, p=0.1, seed=42):
        self.index = _build_note_index(key_records, note_map)
        self.p = float(p)
        self.rng = np.random.default_rng(seed)

    def ask(self, prompt: str) -> str:
        note = _extract_note(prompt)
        if note is None or note not in self.index:
            return _build_response(3, "noisy fallback")
        k = self.index[note]
        true_level = int(k["esi_level"])
        # Draw one uniform value for noise, then one for pick (always consume both).
        noise = float(self.rng.random())
        wrong_pool = [x for x in [1, 2, 3, 4, 5] if x != true_level]
        pick = int(self.rng.choice(wrong_pool))
        if noise < self.p:
            return _build_response(pick, "noisy wrong")
        return _build_response(true_level, "noisy right")


class UnderByOneAdapter(BaseAdapter):
    """Return one step less urgent than the correct level."""

    name = "under_by_one"

    def __init__(self, key_records, note_map):
        self.index = _build_note_index(key_records, note_map)

    def ask(self, prompt: str) -> str:
        note = _extract_note(prompt)
        if note is None or note not in self.index:
            return _build_response(3, "under fallback")
        k = self.index[note]
        true_level = int(k["esi_level"])
        level = min(5, true_level + 1)
        return _build_response(level, "under by one")


class OverByOneAdapter(BaseAdapter):
    """Return one step more urgent than the correct level."""

    name = "over_by_one"

    def __init__(self, key_records, note_map):
        self.index = _build_note_index(key_records, note_map)

    def ask(self, prompt: str) -> str:
        note = _extract_note(prompt)
        if note is None or note not in self.index:
            return _build_response(3, "over fallback")
        k = self.index[note]
        true_level = int(k["esi_level"])
        level = max(1, true_level - 1)
        return _build_response(level, "over by one")


class GarbageAdapter(BaseAdapter):
    """Return a string that holds no JSON and no digit."""

    name = "garbage"

    def __init__(self, key_records=None, note_map=None):
        pass

    def ask(self, prompt: str) -> str:
        return "this is not json at all no numbers here"


class FencedAdapter(BaseAdapter):
    """Return the correct answer in a markdown fence with prose."""

    name = "fenced"

    def __init__(self, key_records, note_map):
        self.index = _build_note_index(key_records, note_map)

    def ask(self, prompt: str) -> str:
        note = _extract_note(prompt)
        if note is None or note not in self.index:
            level = 3
        else:
            level = int(self.index[note]["esi_level"])
        body = json.dumps({"esi_level": level, "reason": "fenced"})
        return (
            "Here is my answer based on the note.\n\n"
            "```json\n" + body + "\n```\n\n"
            "That is my final rating."
        )


class StringLevelAdapter(BaseAdapter):
    """Return the correct level but as a string value."""

    name = "string_level"

    def __init__(self, key_records, note_map):
        self.index = _build_note_index(key_records, note_map)

    def ask(self, prompt: str) -> str:
        note = _extract_note(prompt)
        if note is None or note not in self.index:
            level = 3
        else:
            level = int(self.index[note]["esi_level"])
        return json.dumps({"esi_level": str(level), "reason": "string level"})


class ConditionBestAdapter(BaseAdapter):
    """Return the most common level per condition from the dev split."""

    name = "condition_best"

    def __init__(self, dev_key_records, note_map=None, test_note_map=None):
        # Build per-condition most common level from dev.
        counts = {}
        for k in dev_key_records:
            cond = k["condition_name"]
            lv = int(k["esi_level"])
            counts.setdefault(cond, Counter())[lv] += 1
        self.best = {c: cnt.most_common(1)[0][0] for c, cnt in counts.items()}
        # Build a note index that maps notes to condition names.
        self.note_to_cond = {}
        # Build index for test too if given, by searching both.
        if note_map is not None:
            for k in dev_key_records:
                note = note_map.get(k["id"])
                if note is not None:
                    self.note_to_cond[note] = k["condition_name"]
        if test_note_map is not None:
            # test_note_map is a list of (note, condition) tuples.
            for note, cond in test_note_map:
                self.note_to_cond[note] = cond
        self.fallback = 3

    def ask(self, prompt: str) -> str:
        note = _extract_note(prompt)
        if note is None or note not in self.note_to_cond:
            return _build_response(self.fallback, "condition fallback")
        cond = self.note_to_cond[note]
        level = int(self.best.get(cond, self.fallback))
        return _build_response(level, f"best for {cond}")


MOCK_NAMES = {
    "oracle",
    "always3",
    "random",
    "noisy_oracle_p02",
    "under_by_one",
    "over_by_one",
    "garbage",
    "fenced",
    "string_level",
    "condition_best",
}


def build_mock_adapter(name, dev_key_records, dev_note_map, split_key_records, split_note_map):
    """Return a mock adapter for the given name.

    dev_key_records and dev_note_map always hold dev records.
    split_key_records and split_note_map hold the records of the split under test.
    """
    if name == "oracle":
        return OracleAdapter(split_key_records, split_note_map)
    if name == "always3":
        return Always3Adapter()
    if name == "random":
        return RandomAdapter(seed=42)
    if name == "noisy_oracle_p02":
        a = NoisyOracleAdapter(split_key_records, split_note_map, p=0.2, seed=42)
        a.name = "noisy_oracle_p02"
        return a
    if name == "under_by_one":
        return UnderByOneAdapter(split_key_records, split_note_map)
    if name == "over_by_one":
        return OverByOneAdapter(split_key_records, split_note_map)
    if name == "garbage":
        return GarbageAdapter()
    if name == "fenced":
        return FencedAdapter(split_key_records, split_note_map)
    if name == "string_level":
        return StringLevelAdapter(split_key_records, split_note_map)
    if name == "condition_best":
        test_pairs = [(split_note_map[k["id"]], k["condition_name"]) for k in split_key_records if k["id"] in split_note_map]
        return ConditionBestAdapter(dev_key_records, note_map=dev_note_map, test_note_map=test_pairs)
    raise ValueError(f"unknown mock name: {name}")
