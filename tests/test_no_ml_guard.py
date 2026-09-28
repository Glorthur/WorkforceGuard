"""
No-ML Architectural Guard Test Suite.
Enforces the strict project constraint: zero machine learning model training,
no scikit-learn imports, no RandomForest, no train_test_split, and no predictive regressions
in the active production runtime (src/ and app.py).
"""
import unittest
from pathlib import Path
import re

FORBIDDEN_PATTERNS = [
    r"\bsklearn\b",
    r"\bscikit-learn\b",
    r"\bRandomForest\b",
    r"\btrain_test_split\b",
    r"\bpredict_proba\b",
    r"\btab_predictive\b",
    r"from src\.models\b",
    r"import src\.models\b",
]

class TestNoMLGuard(unittest.TestCase):
    def test_no_ml_in_production_runtime(self):
        """Scans src/ and app.py to guarantee 100% absence of machine learning dependencies."""
        root_dir = Path(__file__).resolve().parents[1]
        paths_to_scan = [root_dir / "app.py"] + list((root_dir / "src").rglob("*.py"))

        violations = []
        for file_path in paths_to_scan:
            # Skip compiled files or non-files
            if "__pycache__" in str(file_path) or not file_path.is_file():
                continue

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            for pattern in FORBIDDEN_PATTERNS:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    violations.append(
                        f"Forbidden ML pattern '{pattern}' found in {file_path.relative_to(root_dir)}: '{match.group(0)}'"
                    )

        self.assertEqual(
            len(violations), 0,
            f"No-ML guard triggered! Found {len(violations)} violations:\n" + "\n".join(violations)
        )

if __name__ == "__main__":
    unittest.main()
