# Підрозділ для рукопису: розширена валідація архітектурних evaluator-ів

Для перевірки меж застосовності `AC_PUBLIC_API` та `AC_MODULE_GRAPH` було проведено EVAL-02 на канонічному вихідному стані A0.4 (`d3101c0d3aa9b7b709253b6ec7518416f05f65b9`, дерево `app/` `007196f68652bc13f6798805793ffdfae96f95f7`). Протокол і каталог із очікуваннями зафіксовано до запуску evaluator-ів у коміті `b9952abd42d507febeafe3217cc7b3f4f0e370dd`, що безпосередньо базується на перевіреному `main` `cd134063e8c1eae37eb3bafe01ce228f02f49493`. Каталог включав 10 умов, зокрема чистий контроль, позитивні форми відносного та локального імпорту, порушення опису публічного контракту, два нові форми залежностей, а також межі динамічного імпорту й неповної специфікації сигнатури. Кожну зміну створено як окремий чистий Git-коміт із канонічним A0.4 як єдиним батьком. Кожен evaluator виконувався тричі для кожної умови; повтори є технічними вимірами одного випадку.

Архітектурний статус, застосовність evaluator-а та очікуваний вихід визначалися окремо. Бінарні метрики включали лише випадки з попередньо визначеним статусом `COMPLIANT`/`NON_COMPLIANT`, де evaluator був застосовним, а всі повтори мали стабільні результати та перевірене походження.

| Evaluator | TP | FP | TN | FN | Застосовних / придатних випадків | Невідомі/некоректні | Precision | Recall | Specificity | Accuracy | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AC_PUBLIC_API | 4 | 0 | 4 | 0 | 8/8 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| AC_MODULE_GRAPH | 2 | 0 | 4 | 0 | 6/6 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

| Випадок | Evaluator | Архітектурний статус | Застосовність | Спостереження за повтореннями | У матриці |
| --- | --- | --- | --- | --- | --- |
| `clean_scope_control` | `AC_PUBLIC_API` | `COMPLIANT` | `APPLICABLE` | COMPLIANT, COMPLIANT, COMPLIANT | так |
| `clean_scope_control` | `AC_MODULE_GRAPH` | `COMPLIANT` | `APPLICABLE` | COMPLIANT, COMPLIANT, COMPLIANT | так |
| `relative_public_import_control` | `AC_PUBLIC_API` | `COMPLIANT` | `APPLICABLE` | COMPLIANT, COMPLIANT, COMPLIANT | так |
| `relative_public_import_control` | `AC_MODULE_GRAPH` | `COMPLIANT` | `APPLICABLE` | COMPLIANT, COMPLIANT, COMPLIANT | так |
| `function_local_public_import_control` | `AC_PUBLIC_API` | `COMPLIANT` | `APPLICABLE` | COMPLIANT, COMPLIANT, COMPLIANT | так |
| `function_local_public_import_control` | `AC_MODULE_GRAPH` | `COMPLIANT` | `APPLICABLE` | COMPLIANT, COMPLIANT, COMPLIANT | так |
| `missing_required_public_function` | `AC_PUBLIC_API` | `NON_COMPLIANT` | `APPLICABLE` | NON_COMPLIANT, NON_COMPLIANT, NON_COMPLIANT | так |
| `missing_required_public_function` | `AC_MODULE_GRAPH` | `COMPLIANT` | `NOT_APPLICABLE_PUBLIC_CONTRACT_CONSTRUCT` | COMPLIANT, COMPLIANT, COMPLIANT | ні |
| `missing_typed_dict_field` | `AC_PUBLIC_API` | `NON_COMPLIANT` | `APPLICABLE` | NON_COMPLIANT, NON_COMPLIANT, NON_COMPLIANT | так |
| `missing_typed_dict_field` | `AC_MODULE_GRAPH` | `COMPLIANT` | `NOT_APPLICABLE_PUBLIC_CONTRACT_CONSTRUCT` | COMPLIANT, COMPLIANT, COMPLIANT | ні |
| `undeclared_public_export` | `AC_PUBLIC_API` | `NON_COMPLIANT` | `APPLICABLE` | NON_COMPLIANT, NON_COMPLIANT, NON_COMPLIANT | так |
| `undeclared_public_export` | `AC_MODULE_GRAPH` | `COMPLIANT` | `NOT_APPLICABLE_PUBLIC_CONTRACT_CONSTRUCT` | COMPLIANT, COMPLIANT, COMPLIANT | ні |
| `aliased_private_service_module_import` | `AC_PUBLIC_API` | `NON_COMPLIANT` | `APPLICABLE` | NON_COMPLIANT, NON_COMPLIANT, NON_COMPLIANT | так |
| `aliased_private_service_module_import` | `AC_MODULE_GRAPH` | `NON_COMPLIANT` | `APPLICABLE` | NON_COMPLIANT, NON_COMPLIANT, NON_COMPLIANT | так |
| `function_local_relative_undeclared_edge` | `AC_PUBLIC_API` | `COMPLIANT` | `APPLICABLE` | COMPLIANT, COMPLIANT, COMPLIANT | так |
| `function_local_relative_undeclared_edge` | `AC_MODULE_GRAPH` | `NON_COMPLIANT` | `APPLICABLE` | NON_COMPLIANT, NON_COMPLIANT, NON_COMPLIANT | так |
| `dynamic_private_module_import_boundary` | `AC_PUBLIC_API` | `NON_COMPLIANT` | `OUT_OF_SCOPE_DYNAMIC_IMPORT` | COMPLIANT, COMPLIANT, COMPLIANT | ні |
| `dynamic_private_module_import_boundary` | `AC_MODULE_GRAPH` | `NON_COMPLIANT` | `OUT_OF_SCOPE_DYNAMIC_IMPORT` | COMPLIANT, COMPLIANT, COMPLIANT | ні |
| `keyword_only_signature_break_boundary` | `AC_PUBLIC_API` | `INDETERMINATE` | `OUT_OF_SCOPE_CALL_SIGNATURE` | COMPLIANT, COMPLIANT, COMPLIANT | ні |
| `keyword_only_signature_break_boundary` | `AC_MODULE_GRAPH` | `COMPLIANT` | `APPLICABLE` | COMPLIANT, COMPLIANT, COMPLIANT | так |

Медіанний час підпроцесу становив 212.824 мс для `AC_PUBLIC_API` та 216.526 мс для `AC_MODULE_GRAPH` (відповідно 30 і 30 валідних завершених викликів). Час є описовим виміром запуску evaluator-а і не відображає часу виконання застосунку чи повного CI.

Результати `NOT_EVALUABLE`: `AC_PUBLIC_API` — немає; `AC_MODULE_GRAPH` — немає.

Динамічний імпорт приватного модуля є архітектурно неприпустимим за зареєстрованими API та графовою вимогами, однак обидва evaluator-и повернули вихід, передбачений для межі їхнього статичного аналізу, і не класифікували цей дефект. Ці спостереження виключено з бінарних метрик через `OUT_OF_SCOPE_DYNAMIC_IMPORT`. Зміна сигнатури на keyword-only порушує позиційний виклик у Reporting, але сигнатура не зафіксована у чинній конфігурації `AC_PUBLIC_API`; її архітектурну оцінку позначено як `INDETERMINATE`, а не як успіх чи помилку evaluator-а.

Отже, EVAL-02 розширює емпіричні спостереження для окремих статичних вихідних шаблонів, але не оцінює точність evaluator-ів у популяції архітектур. До використання цих evaluator-ів як єдиної підстави для твердження про архітектурну валідність у MONO-E1 потрібні додаткові перевірки механізмів поза межами прямого AST-імпорту; їхні поточні результати можуть застосовуватися лише як обмежене, прив'язане до джерела свідчення.
