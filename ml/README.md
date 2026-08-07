# Reproducible learner-skill ML baseline

CyberMentor includes a small, real classical ML component for the submission demo. It classifies a learner's free-text self-assessment into one of four skill areas: `foundations`, `networking`, `linux`, or `soc`.

Pipeline: text input → lowercase/token and bigram features → log-count vectors → multiclass softmax logistic regression → skill label and confidence. The model is trained from `data/learner_skill_samples.csv`, saved to `models/skill_classifier.json`, and evaluated on a deterministic stratified holdout split (one example per class; 32 training rows and 4 test rows in the checked-in run).

The dataset is synthetic/demo data created for reproducible engineering tests. It is not a public benchmark and must not be presented as representative of Lebanese learners. A future pilot should replace or augment it with consented, anonymized learner responses.

```powershell
python ml/train.py
python ml/infer.py "I need help with Linux permissions and chmod"
python -m unittest discover -s ml -p "test_*.py"
```

The saved JSON contains the vocabulary, weights, split sizes, confusion matrix, and accuracy/precision/recall/F1 metrics, so the result is auditable and reproducible without a hidden dependency.
