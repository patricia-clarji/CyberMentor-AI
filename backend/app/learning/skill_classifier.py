"""Load the checked-in, dependency-free learner-skill ML baseline for inference."""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

TOKEN_RE = re.compile(r"[a-z0-9]+")
MODEL_PATH = Path(__file__).resolve().parents[3] / "ml" / "models" / "skill_classifier.json"
LABEL_TO_SKILL = {
    "foundations": "security-foundations",
    "networking": "tcp-ip-reasoning",
    "linux": "linux-processes",
    "soc": "siem-triage",
}


def _features(text: str) -> list[str]:
    tokens = TOKEN_RE.findall(text.lower())
    return tokens + [f"{tokens[index]}__{tokens[index + 1]}" for index in range(len(tokens) - 1)]


def predict(text: str) -> tuple[str, float] | None:
    """Return a mapped skill and confidence, or None when the artifact is unavailable."""
    if not text.strip() or not MODEL_PATH.exists():
        return None
    model: dict[str, Any] = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    vocabulary = model["vocabulary"]
    labels = model["labels"]
    weights = model["weights"]
    bias = model["bias"]
    counts = Counter(_features(text[:4000]))
    vector = [math.log1p(counts.get(token, 0)) for token in vocabulary]
    scores = [
        sum(weight * value for weight, value in zip(row, vector, strict=True)) + item_bias
        for row, item_bias in zip(weights, bias, strict=True)
    ]
    peak = max(scores)
    probabilities = [math.exp(score - peak) for score in scores]
    total = sum(probabilities)
    best = max(range(len(labels)), key=probabilities.__getitem__)
    label = str(labels[best])
    skill = LABEL_TO_SKILL.get(label)
    return (skill, probabilities[best] / total) if skill else None
