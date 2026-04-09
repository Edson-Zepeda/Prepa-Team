from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from student_success.training import save_artifacts


if __name__ == "__main__":
    metadata = save_artifacts()
    print("Model artifacts generated in models/")
    print("Best regression model:", metadata["best_regression_model"])
    print("Good-performance threshold:", metadata["good_performance_threshold"])
    print("Good-performance threshold 0-10:", metadata["good_performance_threshold_10"])
