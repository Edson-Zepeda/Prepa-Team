# Prediction and Analysis of Academic Performance Using Artificial Intelligence

**Authors:** Edson Manuel Zepeda Chavez, Francisco Ricardo Moreno Sanchez, Alan Emir Martinez Espinosa<br>
**Emails:** rmcedson09@gmail.com, fmorenosanchez39@gmail.com, maresesp012@gmail.com<br>
**Affiliations:** Edson Manuel Zepeda Chavez: Samsung Innovation Campus 2025-2026, Universidad de Colima, Bachillerato 16; Francisco Ricardo Moreno Sanchez: Samsung Innovation Campus 2025-2026, CONALEP Plantel 262; Alan Emir Martinez Espinosa: Samsung Innovation Campus 2025-2026, CONALEP Plantel 262<br>
**Repository:** https://github.com/Edson-Zepeda/Prepa-Team<br>
**Main format:** IEEE/IMRaD LaTeX in `Paper_GPA_English.tex`

> Optional logos: the English LaTeX file uses `logo_udem.png` and `logo_sic.png` from `paper/figures/` if they exist.

## Abstract

This article presents an artificial intelligence system, based on machine learning, for predicting and analyzing student academic performance and translating model outputs into actionable early-intervention recommendations. The study uses a tabular dataset of 2,392 students and 15 variables, including age, weekly study time, absences, tutoring, parental support, extracurricular activities, and GPA. The approach combines regression for GPA estimation and calibrated classification for estimating the probability of achieving good performance, defined as `GPA >= 2.5`.

The best regression model was `LinearRegression`, with `RMSE = 0.1963` and `R2 = 0.9534` on the test set. After hyperparameter tuning, `XGBoost` reduced its test RMSE to `0.2028` and remained highly similar to the linear model (`correlation = 0.9979`), but it still did not generalize better. Removing `Absences` increased the linear model RMSE from `0.1963` to `0.8692`, confirming that absences are the dominant factor. Finally, a recommendation engine was implemented to simulate interventions, exclude sensitive or non-actionable variables, and prioritize actions with the highest estimated impact on GPA and probability of good performance.

**Keywords:** academic performance, GPA, machine learning, Educational Data Mining, XGBoost, academic recommendations, early warning, interpretability.

## 1. Introduction

Early prediction of academic performance can help tutors, teachers, and coordinators identify at-risk students. However, prediction alone is not enough for school use: the practical question is not only what GPA is expected, but also what actions can increase the probability of good performance.

This project builds a complete workflow: predict GPA, compare models, analyze why `XGBoost` does not outperform the linear model, measure the impact of `Absences`, train a good-performance classifier, and generate actionable recommendations. The main story of the paper is the transition from a predictive model to a support tool for supervised academic interventions.

## 2. Data

The local file `student_performance.csv` contains:

- `2392` records
- `15` columns
- `0` missing values
- observed `GPA` from `0.0` to `4.0`
- mean `GPA` of `1.9062`
- `706` students with `GPA >= 2.5`
- `1686` students with `GPA < 2.5`

The dataset source is Kaggle, **Students Performance Dataset**, by Rabie El Kharoua.

![GPA distribution](figures/fig_gpa_distribution.png)

![Good-performance class balance](figures/fig_good_performance_balance.png)

## 3. Methodology

For regression, `GPA` was used as the target. `StudentID` and `GradeClass` were removed: `StudentID` does not generalize, and `GradeClass` introduces data leakage because it summarizes performance. Preprocessing was implemented with `Pipeline` and `ColumnTransformer`: median imputation for numeric variables, most-frequent imputation for categorical variables, scaling with `StandardScaler`, and encoding with `OneHotEncoder`.

An 80/20 train-test split with `random_state = 42` and 5-fold cross-validation were used. The compared regression models were:

- `LinearRegression`
- `RandomForestRegressor`
- `SVR` with RBF kernel
- `XGBRegressor`

For recommendations, a good-performance classifier was trained:

```text
1 = GPA >= 2.5
0 = GPA < 2.5
```

The evaluated classifiers were `LogisticRegression`, `RandomForestClassifier`, `HistGradientBoostingClassifier`, and `XGBClassifier`. The best classifier was calibrated with `CalibratedClassifierCV` to produce more interpretable probabilities.

The recommendation engine excludes:

- `StudentID`
- `GradeClass`
- `Gender`
- `Ethnicity`

And simulates changes on:

- `Absences`
- `StudyTimeWeekly`
- `Tutoring`
- `ParentalSupport`
- `Extracurricular`
- `Sports`
- `Music`
- `Volunteering`

## 4. Results

### 4.1 Regression Models

| Model | Test MAE | Test RMSE | Test R2 | CV RMSE | CV R2 |
|---|---:|---:|---:|---:|---:|
| LinearRegression | 0.1551 | 0.1963 | 0.9534 | 0.1974 | 0.9533 |
| XGBoost | 0.1584 | 0.2028 | 0.9503 | 0.2043 | 0.9500 |
| SVR RBF | 0.2024 | 0.2520 | 0.9232 | 0.2491 | 0.9257 |
| Random Forest | 0.1964 | 0.2529 | 0.9226 | 0.2460 | 0.9275 |

The best model was `LinearRegression`. Cross-validation was very close to the test result, indicating stable performance.

![Model comparison](figures/fig_model_comparison.png)

![Actual vs predicted](figures/fig_actual_vs_predicted.png)

### 4.2 XGBoost Analysis

| Model | Train RMSE | Test RMSE | Gap RMSE | Test R2 |
|---|---:|---:|---:|---:|
| LinearRegression | 0.1960 | 0.1963 | 0.0003 | 0.9534 |
| XGBoost | 0.1811 | 0.2028 | 0.0217 | 0.9503 |

After hyperparameter tuning, `XGBoost` reduced its error considerably compared with the initial configuration, but it still did not outperform `LinearRegression`. Their predictions remain highly correlated (`0.9979`), with a mean absolute difference of `0.0453`. The interpretation is that `XGBoost` captures more structure, but the dataset still favors an almost linear solution.

![LinearRegression vs XGBoost predictions](figures/fig_xgb_lr_predictions.png)

### 4.3 Feature Importance and Absences Ablation

The most important variables were:

| Variable | Mean importance |
|---|---:|
| Absences | 1.0056 |
| ParentalSupport | 0.1225 |
| StudyTimeWeekly | 0.1013 |
| Tutoring | 0.0519 |
| Sports | 0.0413 |

The correlation between `Absences` and `GPA` was `-0.9193`.

![Feature importance](figures/fig_feature_importance.png)

| Model | Base RMSE | RMSE without Absences | Delta RMSE | R2 without Absences |
|---|---:|---:|---:|---:|
| LinearRegression | 0.1963 | 0.8692 | 0.6729 | 0.0864 |
| XGBoost | 0.2028 | 0.8958 | 0.6931 | 0.0295 |
| Random Forest | 0.2529 | 0.9278 | 0.6749 | -0.0411 |
| SVR RBF | 0.2520 | 1.0753 | 0.8233 | -0.3984 |

The performance drop confirms that `Absences` concentrates the main signal of the dataset. Even with tuned `XGBoost`, the model remains slightly below the linear baseline when that variable is removed.

![Ablation without Absences](figures/fig_ablation_absences.png)

### 4.4 Good-Performance Classifier

The best calibrated classifier was `logistic_regression_calibrated`.

| ROC AUC | Avg. Precision | Accuracy | Precision | Recall | F1 | Brier |
|---:|---:|---:|---:|---:|---:|---:|
| 0.9871 | 0.9704 | 0.9478 | 0.9143 | 0.9078 | 0.9110 | 0.0412 |

![Confusion matrix](figures/fig_confusion_matrix.png)

![ROC and PR curves](figures/fig_roc_pr_curves.png)

### 4.5 Student Recommendations

For a moderate-to-high risk case, the best simulated plan was:

```text
reduce absences by 10
increase study time up to 20h/week
enable tutoring
increase parental support by 1
enable Extracurricular
```

Estimated impact:

| Current GPA | Estimated GPA | Current probability | Estimated probability |
|---:|---:|---:|---:|
| 2.2783 | 4.0000 | 14.85% | 99.999% |

This result is a simulation, not a causal guarantee.

![Recommended plan](figures/fig_recommendation_plan.png)

### 4.6 Basic Fairness Audit

Although `Gender` and `Ethnicity` are not used to recommend actions, group-level metrics were evaluated to detect risks. Accuracy by `Gender` was `0.9375` for group 0 and `0.9582` for group 1. By `Ethnicity`, accuracy ranged from `0.9130` to `0.9637`. This does not prove causal bias, but it justifies subgroup monitoring before school deployment.

![Fairness audit](figures/fig_fairness_audit.png)

## 5. Discussion

The central result is that the most complex model was not the best. Even after tuning, `XGBoost` did not generalize better than `LinearRegression`. The likely reason is that the dataset has a dominant and nearly linear relationship between `Absences` and `GPA`.

The usefulness of the project is in the recommendation layer. The system not only predicts, but also simulates scenarios and prioritizes actions. This makes it closer to an early-warning tool for tutors and students.

## 6. Ethical Considerations and Limitations

The system must not be used to sanction, exclude, or automatically label students. The recommendations are model simulations, not causal evidence. Before using it in a real school, local validation, human supervision, and periodic auditing are required.

Main limitations:

- Institutional use requires validation with local school data.
- The dataset is not longitudinal.
- The recommendations are simple counterfactual simulations.
- Context variables such as health, academic workload, socioeconomic status, and teaching quality are missing.
- The intensive plan maximizes the result under simulated rules, but its real feasibility depends on the student and school.

## 7. Conclusion

The project shows that it is possible to build an interpretable system for GPA prediction and academic intervention recommendations. `LinearRegression` was the best regressor, tuned `XGBoost` narrowed the gap but did not surpass it, `Absences` was the dominant variable, and the calibrated classifier allowed simulated changes to be translated into good-performance probabilities.

The natural next step is to convert the notebook into a school demo platform with CSV upload, individual student profiles, an intervention simulator, tutor reports, and ethical subgroup monitoring.

## Main References

- Rabie El Kharoua. *Students Performance Dataset*. Kaggle. https://www.kaggle.com/datasets/rabieelkharoua/students-performance-dataset
- Dalia Khairy et al. *Prediction of student exam performance using data mining classification algorithms*. Education and Information Technologies. https://link.springer.com/article/10.1007/s10639-024-12619-w
- Pedregosa et al. *Scikit-learn: Machine Learning in Python*. Journal of Machine Learning Research. https://www.jmlr.org/papers/v12/pedregosa11a.html
- Chen and Guestrin. *XGBoost: A Scalable Tree Boosting System*. https://arxiv.org/abs/1603.02754
