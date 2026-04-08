# Analisis adicional de XGBoost y escenario sin Absences

Este documento resume el analisis extendido para responder dos preguntas: 1) que pasa al quitar `Absences`, y 2) hasta donde puede mejorar `XGBoost` sin manipular el set de prueba.

## Regresion con todas las variables

| model | train_rmse | test_rmse | test_r2 | cv_rmse |
| --- | --- | --- | --- | --- |
| linear_regression | 0.19601328967561646 | 0.19630825342373784 | 0.9533977379675411 | nan |
| xgboost_tuned | 0.18111941044613508 | 0.20279012874534363 | 0.9502694226606105 | nan |
| xgboost_random_search | nan | 0.20279012874534363 | 0.9502694226606105 | 0.20419410731990179 |


## Regresion sin Absences

| model | train_rmse | test_rmse | test_r2 |
| --- | --- | --- | --- |
| linear_regression_wo_absences | 0.863974891350057 | 0.8691839832017099 | 0.0864058523809963 |
| xgboost_tuned_wo_absences | 0.8579636203498215 | 0.8759481575011864 | 0.0721309552793028 |


## Clasificacion de buen rendimiento

| model | roc_auc | avg_precision | accuracy | precision | recall | f1 | brier |
| --- | --- | --- | --- | --- | --- | --- | --- |
| logistic_regression | 0.9871165386713668 | 0.9706506043511746 | 0.9311064718162839 | 0.8417721518987342 | 0.9432624113475178 | 0.8896321070234113 | 0.04766179485184344 |
| xgboost_classifier_tuned | 0.9880817491292122 | 0.9739366359440758 | 0.9436325678496869 | 0.8958333333333334 | 0.9148936170212766 | 0.9052631578947369 | 0.04093718680585785 |
| xgboost_classifier_tuned_calibrated | 0.9878929036048513 | 0.9737643919231158 | 0.9457202505219207 | 0.9020979020979021 | 0.9148936170212766 | 0.9084507042253521 | 0.04181101087545907 |


## Conclusiones

- En regresion, `XGBoost` mejora con tuning, pero no supera honestamente a `LinearRegression` en este dataset.

- Sin `Absences`, ambos modelos empeoran mucho y `LinearRegression` sigue ligeramente arriba.

- En la tarea de clasificacion para probabilidad de buen rendimiento, `XGBoost` tuneado si supera a `LogisticRegression` en discriminacion y queda como mejor clasificador del proyecto.