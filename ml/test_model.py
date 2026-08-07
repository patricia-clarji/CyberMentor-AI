import json
import unittest
from pathlib import Path
from infer import predict
class ModelSmokeTest(unittest.TestCase):
    def test_saved_model_predicts_expected_demo_skills(self) -> None:
        model_path = Path(__file__).parent / "models/skill_classifier.json"; self.assertTrue(model_path.exists(), "Run python ml/train.py first")
        model = json.loads(model_path.read_text(encoding="utf-8"))
        self.assertEqual(predict("I need help with Linux permissions and chmod", model)[0], "linux")
        self.assertEqual(predict("I need practice investigating alerts and writing a short incident timeline", model)[0], "soc")
        self.assertEqual(predict("Please explain subnetting and routing", model)[0], "networking")
if __name__ == "__main__": unittest.main()
