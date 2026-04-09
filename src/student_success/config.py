from pathlib import Path

RANDOM_STATE = 42
ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT_DIR / "data" / "raw" / "student_performance.csv"
MODEL_DIR = ROOT_DIR / "models"
ARTIFACT_PATH = MODEL_DIR / "student_success_artifacts.joblib"
METADATA_PATH = MODEL_DIR / "student_success_metadata.json"

TARGET = "GPA"
MEXICAN_SCALE_FACTOR = 2.5
GOOD_PERFORMANCE_THRESHOLD_10 = 6.0
GOOD_PERFORMANCE_THRESHOLD = GOOD_PERFORMANCE_THRESHOLD_10 / MEXICAN_SCALE_FACTOR

DROP_COLUMNS = ["StudentID", "GradeClass"]
REGRESSION_NUMERIC_FEATURES = ["Age", "StudyTimeWeekly", "Absences"]
REGRESSION_CATEGORICAL_FEATURES = [
    "Gender",
    "Ethnicity",
    "ParentalEducation",
    "Tutoring",
    "ParentalSupport",
    "Extracurricular",
    "Sports",
    "Music",
    "Volunteering",
]

ADVICE_NUMERIC_FEATURES = ["Age", "StudyTimeWeekly", "Absences"]
ADVICE_CATEGORICAL_FEATURES = [
    "ParentalEducation",
    "Tutoring",
    "ParentalSupport",
    "Extracurricular",
    "Sports",
    "Music",
    "Volunteering",
]
ADVICE_FEATURES = ADVICE_NUMERIC_FEATURES + ADVICE_CATEGORICAL_FEATURES
ACTIONABLE_FEATURES = [
    "StudyTimeWeekly",
    "Absences",
    "Tutoring",
    "ParentalSupport",
    "Extracurricular",
    "Sports",
    "Music",
    "Volunteering",
]
EXCLUDED_FROM_ADVICE = ["StudentID", "GradeClass", "Gender", "Ethnicity"]

FIELD_LIMITS = {
    "Age": (10, 25),
    "StudyTimeWeekly": (0, 20),
    "Absences": (0, 30),
    "ParentalEducation": (0, 4),
    "Tutoring": (0, 1),
    "ParentalSupport": (0, 4),
    "Extracurricular": (0, 1),
    "Sports": (0, 1),
    "Music": (0, 1),
    "Volunteering": (0, 1),
}
