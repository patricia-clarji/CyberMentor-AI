"""Run inference with the saved CyberMentor learner-skill model."""
from __future__ import annotations
import json, math, re, sys
from collections import Counter
from pathlib import Path
MODEL = Path(__file__).resolve().parent / "models/skill_classifier.json"
TOKEN_RE = re.compile(r"[a-z0-9]+")
def predict(text: str, model: dict[str, object]) -> tuple[str, float]:
    vocabulary, labels = model["vocabulary"], model["labels"]; weights, bias = model["weights"], model["bias"]
    assert isinstance(vocabulary, list) and isinstance(labels, list)
    tokens = TOKEN_RE.findall(text.lower()); all_tokens = tokens + [f"{tokens[i]}__{tokens[i + 1]}" for i in range(len(tokens) - 1)]; counts = Counter(all_tokens)
    vector = [math.log1p(counts.get(token, 0)) for token in vocabulary]
    scores = [sum(weight * value for weight, value in zip(row, vector)) + b for row, b in zip(weights, bias)]; peak = max(scores); probabilities = [math.exp(score - peak) for score in scores]; total = sum(probabilities); best = max(range(len(labels)), key=lambda i: probabilities[i])
    return str(labels[best]), probabilities[best] / total
if __name__ == "__main__":
    if not MODEL.exists(): raise SystemExit("Model missing. Run: python ml/train.py")
    question = " ".join(sys.argv[1:]).strip() or "I need help understanding Linux permissions"; label, confidence = predict(question, json.loads(MODEL.read_text(encoding="utf-8")))
    print(json.dumps({"text": question, "predicted_skill": label, "confidence": round(confidence, 4)}))
