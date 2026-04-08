# Sistema predictivo e interpretable para recomendacion de intervenciones academicas basadas en GPA

**Autores:** Edson Zepeda y equipo  
**Repositorio:** https://github.com/Edson-Zepeda/proyecto-gpa  
**Estado:** Borrador academico para revision  

## Resumen

Este trabajo presenta un sistema de analisis predictivo orientado a estimar el rendimiento academico de estudiantes y traducir los resultados del modelo en recomendaciones accionables. Se utilizo un conjunto de datos estructurado con 2,392 registros y 15 variables, incluyendo edad, tiempo semanal de estudio, ausencias, apoyo parental, tutorias, actividades extracurriculares y GPA. El objetivo principal fue predecir el GPA mediante modelos de regresion y, adicionalmente, construir un clasificador para estimar la probabilidad de alcanzar buen rendimiento academico, definido como `GPA >= 2.5`. Se compararon modelos lineales, Random Forest, SVR y XGBoost. El mejor modelo de regresion fue `LinearRegression`, con `RMSE = 0.1963` y `R2 = 0.9534` en el conjunto de prueba. Aunque XGBoost mostro predicciones altamente correlacionadas con el modelo lineal, presento mayor diferencia entre entrenamiento y prueba, lo que sugiere sobreajuste relativo. La prueba de ablacion sin la variable `Absences` mostro una degradacion considerable del desempeno, elevando el RMSE del modelo lineal de `0.1963` a `0.8692`, confirmando que las ausencias son el factor mas dominante del conjunto de datos. Finalmente, se incorporo un motor de recomendaciones que simula intervenciones factibles, excluye variables sensibles y propone planes de mejora ordenados por su impacto estimado en GPA y probabilidad de buen rendimiento. El sistema resultante no solo predice el rendimiento, sino que ayuda a identificar acciones concretas para apoyar al estudiante.

**Palabras clave:** rendimiento academico, GPA, aprendizaje automatico, XGBoost, recomendaciones academicas, alerta temprana, interpretabilidad.

## 1. Introduccion

La prediccion temprana del rendimiento academico puede apoyar a docentes, tutores y coordinadores academicos en la identificacion de estudiantes que requieren intervenciones oportunas. Sin embargo, un modelo predictivo por si solo no es suficiente si no proporciona informacion accionable. En un contexto educativo, no basta con estimar que un estudiante podria tener bajo rendimiento; tambien es necesario explicar que factores contribuyen al riesgo y que acciones podrian modificar el resultado esperado.

Este proyecto parte de un conjunto de datos de desempeno estudiantil y desarrolla un flujo de trabajo reproducible para:

1. Predecir el GPA de un estudiante.
2. Comparar modelos de regresion.
3. Analizar el comportamiento de XGBoost frente al modelo lineal.
4. Evaluar la importancia de `Absences` mediante una prueba de ablacion.
5. Entrenar un clasificador de buen rendimiento academico (`GPA >= 2.5`).
6. Generar recomendaciones accionables para el estudiante.

El aporte principal del proyecto es pasar de una prediccion numerica a una herramienta orientada a decision: el sistema estima el estado actual del estudiante, simula planes de mejora y documenta mensajes explicables para uso academico.

## 2. Datos

El conjunto de datos contiene 2,392 registros y 15 columnas. Las variables disponibles son:

- `StudentID`: identificador del estudiante.
- `Age`: edad.
- `Gender`: genero codificado.
- `Ethnicity`: etnia codificada.
- `ParentalEducation`: nivel educativo de los padres codificado.
- `StudyTimeWeekly`: horas de estudio por semana.
- `Absences`: numero de ausencias.
- `Tutoring`: indicador de tutorias.
- `ParentalSupport`: nivel de apoyo parental.
- `Extracurricular`: participacion extracurricular.
- `Sports`: participacion en deportes.
- `Music`: participacion en musica.
- `Volunteering`: participacion en voluntariado.
- `GPA`: promedio academico.
- `GradeClass`: clase o nivel de rendimiento codificado.

No se detectaron valores faltantes. Para evitar fuga de informacion, se excluyeron `StudentID` y `GradeClass` al entrenar los modelos de prediccion del GPA. `StudentID` no es una variable informativa para generalizar y `GradeClass` resume el rendimiento, por lo que usarla para predecir GPA podria introducir leakage.

Para el motor de recomendaciones se aplico una restriccion adicional: se excluyeron `Gender`, `Ethnicity`, `StudentID` y `GradeClass`. Esta decision se tomo porque el objetivo del sistema no es recomendar cambios sobre variables sensibles o no accionables, sino proponer intervenciones practicas.

## 3. Metodologia

### 3.1 Preprocesamiento

El flujo de preprocesamiento se implemento con pipelines de `scikit-learn` para evitar fuga de informacion entre entrenamiento y prueba. Las variables numericas se imputaron con la mediana y se escalaron con `StandardScaler`. Las variables categoricas codificadas se imputaron con la moda y se transformaron con `OneHotEncoder`.

Se uso una particion `train/test` de 80/20 con `random_state = 42`. Ademas, se evaluo estabilidad mediante validacion cruzada de 5 particiones.

### 3.2 Modelos de regresion

Se entrenaron y compararon los siguientes modelos para predecir GPA:

- `LinearRegression`
- `RandomForestRegressor`
- `SVR` con kernel RBF
- `XGBRegressor`

La evaluacion se realizo con:

- `MAE`: error absoluto medio.
- `RMSE`: raiz del error cuadratico medio.
- `R2`: proporcion de varianza explicada.

### 3.3 Analisis de XGBoost

El profesor senalo que XGBoost aparecia muy cercano al modelo lineal y que esto requeria analisis. Para responderlo, se compararon metricas de entrenamiento, prueba y validacion cruzada entre `LinearRegression` y `XGBoost`. Tambien se midio la correlacion entre las predicciones de ambos modelos.

El resultado mostro que XGBoost produce predicciones muy parecidas a las del modelo lineal, con una correlacion aproximada de `0.9957`. Sin embargo, XGBoost tuvo menor error en entrenamiento y mayor error en prueba, lo cual sugiere sobreajuste relativo.

### 3.4 Prueba sin `Absences`

Para evaluar la dependencia del modelo respecto a la variable `Absences`, se entrenaron nuevamente los modelos removiendo dicha variable. Esta prueba permite estimar la contribucion de las ausencias al desempeno predictivo.

### 3.5 Clasificador de buen rendimiento

Para convertir el sistema en una herramienta de recomendacion, se definio una variable binaria:

```text
1 = GPA >= 2.5
0 = GPA < 2.5
```

Se entrenaron clasificadores para estimar la probabilidad de alcanzar buen rendimiento. Los modelos evaluados fueron:

- `LogisticRegression`
- `RandomForestClassifier`
- `HistGradientBoostingClassifier`
- `XGBClassifier`

Las metricas usadas fueron:

- `ROC AUC`
- `Average Precision`
- `Accuracy`
- `Precision`
- `Recall`
- `F1`
- `Brier Score`

El mejor clasificador fue calibrado para que sus probabilidades fueran mas interpretables. La calibracion permite que una probabilidad reportada sea mas util para comparar escenarios.

### 3.6 Motor de recomendaciones

El motor de recomendaciones simula cambios sobre variables accionables:

- Reducir ausencias.
- Aumentar horas de estudio.
- Activar tutorias.
- Incrementar apoyo parental.
- Activar participacion extracurricular, deportiva, musical o voluntariado cuando corresponda.

Para cada intervencion se calcula:

- GPA actual estimado.
- GPA estimado despues del plan.
- Cambio estimado en GPA.
- Probabilidad actual de buen rendimiento.
- Probabilidad estimada despues del plan.
- Cambio en puntos porcentuales.

El sistema ordena los planes por mayor incremento de probabilidad y GPA, considerando tambien un valor de esfuerzo. Esto permite proponer un plan que sea mas util para el estudiante y para el tutor.

## 4. Resultados

### 4.1 Comparacion de modelos de regresion

| Modelo | Test MAE | Test RMSE | Test R2 | CV RMSE | CV R2 |
|---|---:|---:|---:|---:|---:|
| LinearRegression | 0.1551 | 0.1963 | 0.9534 | 0.1974 | 0.9533 |
| XGBoost | 0.1656 | 0.2117 | 0.9458 | 0.2138 | 0.9452 |
| SVR RBF | 0.2024 | 0.2520 | 0.9232 | 0.2491 | 0.9257 |
| Random Forest | 0.1964 | 0.2529 | 0.9226 | 0.2460 | 0.9275 |

El modelo lineal tuvo el mejor desempeno en prueba y validacion cruzada. Esto sugiere que, para este conjunto de datos, la relacion entre las variables disponibles y el GPA es capturada de forma suficiente por un modelo lineal.

### 4.2 Analisis de XGBoost

| Modelo | Train RMSE | Test RMSE | CV RMSE | Train R2 | Test R2 | CV R2 |
|---|---:|---:|---:|---:|---:|---:|
| LinearRegression | 0.1960 | 0.1963 | 0.1974 | 0.9542 | 0.9534 | 0.9533 |
| XGBoost | 0.1381 | 0.2117 | 0.2138 | 0.9773 | 0.9458 | 0.9452 |

XGBoost logro un RMSE mucho menor en entrenamiento, pero no en prueba. Esto indica que el modelo tiene mayor capacidad para ajustar patrones del entrenamiento, pero no generalizo mejor que el modelo lineal. Por esta razon no se selecciono como modelo final de regresion, aunque sus predicciones fueran altamente similares a las del modelo lineal.

### 4.3 Prueba sin `Absences`

| Modelo | RMSE base | RMSE sin Absences | Delta RMSE | R2 base | R2 sin Absences |
|---|---:|---:|---:|---:|---:|
| LinearRegression | 0.1963 | 0.8692 | 0.6729 | 0.9534 | 0.0864 |
| Random Forest | 0.2529 | 0.9278 | 0.6749 | 0.9226 | -0.0411 |
| XGBoost | 0.2117 | 0.9398 | 0.7281 | 0.9458 | -0.0681 |
| SVR RBF | 0.2520 | 1.0753 | 0.8233 | 0.9232 | -0.3984 |

La eliminacion de `Absences` redujo de forma considerable el desempeno de todos los modelos. Esto confirma que las ausencias son el factor predictivo mas fuerte del conjunto de datos.

### 4.4 Clasificador de buen rendimiento

El clasificador calibrado obtuvo:

| Modelo | ROC AUC | Avg. Precision | Accuracy | Precision | Recall | F1 | Brier |
|---|---:|---:|---:|---:|---:|---:|---:|
| LogisticRegression calibrado | 0.9871 | 0.9704 | 0.9478 | 0.9143 | 0.9078 | 0.9110 | 0.0412 |

Estos resultados indican que el clasificador separa adecuadamente a estudiantes con buen rendimiento (`GPA >= 2.5`) de aquellos por debajo del umbral. El Brier score bajo sugiere que las probabilidades estimadas son razonablemente utiles para comparar escenarios.

### 4.5 Recomendaciones generadas

En un caso de demostracion de riesgo alto, el sistema genero un plan combinado que incluia:

- Reducir ausencias.
- Aumentar horas de estudio.
- Activar tutorias.
- Incrementar apoyo parental.
- Activar una actividad extracurricular.

El plan recomendado mostro un aumento estimado de GPA de `0.16` a `2.64` y una probabilidad de buen rendimiento de `0.0%` a `78.9%`. Estos valores no deben interpretarse como garantia, sino como una simulacion para priorizar acciones.

## 5. Discusion

Los resultados muestran tres hallazgos centrales. Primero, el modelo lineal fue el mas estable para predecir GPA, superando a modelos mas complejos como XGBoost, Random Forest y SVR. Segundo, el analisis de XGBoost mostro que la mayor capacidad del modelo no necesariamente mejora la generalizacion. Tercero, la variable `Absences` domina la prediccion, lo cual convierte la reduccion de ausencias en una intervencion prioritaria.

El motor de recomendaciones agrega una capa practica al sistema. En lugar de limitarse a reportar una prediccion, permite probar escenarios y convertir el modelo en una herramienta de apoyo para estudiantes y tutores. Esto es especialmente relevante en un entorno escolar, donde el objetivo no debe ser etiquetar a un estudiante, sino identificar acciones que puedan mejorar su trayectoria academica.

## 6. Consideraciones eticas

El uso de modelos predictivos en educacion debe realizarse con cuidado. El sistema no debe utilizarse para excluir, sancionar o etiquetar automaticamente a estudiantes. Las recomendaciones deben entenderse como apoyo a la decision y no como una decision automatica.

Para recomendaciones, el proyecto excluye variables sensibles o no accionables como `Gender`, `Ethnicity`, `StudentID` y `GradeClass`. Esta separacion reduce el riesgo de sugerir acciones imposibles o eticamente inapropiadas. Aun asi, antes de implementar el sistema en una escuela real, se recomienda validar el modelo con datos locales, revisar sesgos y establecer supervision humana.

## 7. Limitaciones

Este trabajo tiene limitaciones importantes:

- La fuente publica exacta del dataset debe documentarse antes de una publicacion formal.
- El conjunto de datos no incluye informacion temporal, por lo que no se modela evolucion del estudiante a lo largo del tiempo.
- Las recomendaciones son simulaciones contrafactuales simples, no evidencia causal.
- El sistema requiere validacion con datos reales de la institucion antes de ser usado en decisiones academicas.
- Las variables disponibles no capturan todos los factores que influyen en el rendimiento, como salud, contexto socioeconomico, calidad docente o carga academica.

## 8. Conclusion

El proyecto demuestra que es posible construir un sistema interpretable para prediccion de GPA y recomendacion de intervenciones academicas. El modelo lineal fue el mejor regresor, con `RMSE = 0.1963` y `R2 = 0.9534`. La prueba sin `Absences` confirmo que las ausencias son el factor mas influyente. Adicionalmente, el clasificador de buen rendimiento permitio estimar probabilidades de alcanzar `GPA >= 2.5`, lo que hizo posible generar planes de accion personalizados.

El siguiente paso para convertir este trabajo en una plataforma escolar real es integrar el notebook en una aplicacion web con captura de casos, carga de CSV, visualizacion de riesgo, simulacion de intervenciones y reportes para tutores. Esta version deberia mantener supervision humana y controles eticos para evitar decisiones automatizadas no justificadas.

## Referencias

Breiman, L. (2001). Random Forests. *Machine Learning*, 45(1), 5-32. https://doi.org/10.1023/A:1010933404324

Chen, T., & Guestrin, C. (2016). XGBoost: A Scalable Tree Boosting System. *Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining*. https://arxiv.org/abs/1603.02754

Cortes, C., & Vapnik, V. (1995). Support-vector networks. *Machine Learning*, 20, 273-297. https://doi.org/10.1007/BF00994018

Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., Grisel, O., Blondel, M., Prettenhofer, P., Weiss, R., Dubourg, V., Vanderplas, J., Passos, A., Cournapeau, D., Brucher, M., Perrot, M., & Duchesnay, E. (2011). Scikit-learn: Machine Learning in Python. *Journal of Machine Learning Research*, 12(85), 2825-2830. https://www.jmlr.org/papers/v12/pedregosa11a.html

