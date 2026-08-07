"""Train/evaluate a dependency-free multiclass logistic-regression baseline."""
from __future__ import annotations
import csv, json, math, random, re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA, MODEL = ROOT / "data/learner_skill_samples.csv", ROOT / "models/skill_classifier.json"
TOKEN_RE = re.compile(r"[a-z0-9]+")

def features(text: str) -> list[str]:
    tokens = TOKEN_RE.findall(text.lower())
    return tokens + [f"{tokens[i]}__{tokens[i + 1]}" for i in range(len(tokens) - 1)]

def load_rows() -> list[tuple[str, str]]:
    with DATA.open(newline="", encoding="utf-8") as handle:
        return [(row["text"], row["label"]) for row in csv.DictReader(handle)]

def softmax(values: list[float]) -> list[float]:
    peak = max(values); exps = [math.exp(value - peak) for value in values]; total = sum(exps)
    return [value / total for value in exps]

def train(rows: list[tuple[str, str]], seed: int = 7) -> dict[str, object]:
    grouped: dict[str, list[tuple[str, str]]] = {}
    for row in rows: grouped.setdefault(row[1], []).append(row)
    rng = random.Random(seed)
    train_rows, test_rows = [], []
    for group in grouped.values():
        rng.shuffle(group); test_rows.append(group.pop()); train_rows.extend(group)
    labels = sorted({label for _, label in rows}); vocabulary = sorted({t for text, _ in train_rows for t in features(text)})
    index = {token: i for i, token in enumerate(vocabulary)}; weights = [[0.0] * len(vocabulary) for _ in labels]; bias = [0.0] * len(labels)
    label_index = {label: i for i, label in enumerate(labels)}
    def vector(text: str) -> list[float]:
        counts = Counter(features(text)); return [math.log1p(counts.get(token, 0)) for token in vocabulary]
    for _ in range(350):
        for text, label in train_rows:
            x = vector(text); probabilities = softmax([sum(w * value for w, value in zip(row, x)) + b for row, b in zip(weights, bias)])
            target = label_index[label]
            for class_index in range(len(labels)):
                error = probabilities[class_index] - (class_index == target); bias[class_index] -= 0.35 * error
                for feature_index, value in enumerate(x): weights[class_index][feature_index] -= 0.35 * error * value
    def predict(text: str) -> str:
        x = vector(text); p = softmax([sum(w * value for w, value in zip(row, x)) + b for row, b in zip(weights, bias)])
        return labels[max(range(len(labels)), key=p.__getitem__)]
    confusion = {label: {other: 0 for other in labels} for label in labels}
    for text, expected in test_rows: confusion[expected][predict(text)] += 1
    correct = sum(confusion[label][label] for label in labels); total = len(test_rows)
    metrics: dict[str, float] = {"accuracy": correct / total if total else 0.0}
    for label in labels:
        tp = confusion[label][label]; fp = sum(confusion[other][label] for other in labels if other != label); fn = sum(confusion[label][other] for other in labels if other != label)
        precision = tp / (tp + fp) if tp + fp else 0.0; recall = tp / (tp + fn) if tp + fn else 0.0
        metrics.update({f"{label}_precision": precision, f"{label}_recall": recall, f"{label}_f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0})
    model = {"model": "multiclass_logistic_regression", "seed": seed, "labels": labels, "vocabulary": vocabulary, "weights": weights, "bias": bias, "split": {"train_rows": len(train_rows), "test_rows": len(test_rows)}, "metrics": metrics, "confusion": confusion}
    MODEL.parent.mkdir(parents=True, exist_ok=True); MODEL.write_text(json.dumps(model, indent=2) + "\n", encoding="utf-8"); return model

if __name__ == "__main__":
    result = train(load_rows()); print(json.dumps({"model": result["model"], "split": result["split"], "metrics": result["metrics"]}, indent=2))
