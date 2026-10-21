# Шаблон звіту MONO-E1 / MONO-E2

> Заповнювати лише за перевіреними артефактами. Видаліть цей блок після завершення звіту. Не замінюйте `UNKNOWN`, `NOT_RUN`, `NOT_EVALUABLE` або `NOT_COLLECTED` припущенням чи нулем.

## Реєстрація дослідження

- Ідентифікатор: `[[MONO-E1 | MONO-E2]]`
- Статус: `[[NOT_RUN | PLANNED | FROZEN | EXECUTED | SCORED | BLOCKED]]`
- Вплив сценарію: `KNOWN_SCENARIO_AUTHOR_DECLARED`
- Автор референсу: `[[ідентифікатор або UNKNOWN]]`
- Статус зберігання референсу: `[[AUTHOR_DECLARED | NOT_ESTABLISHED]]`
- SHA-256 референсу: `[[digest або UNKNOWN]]`
- Час фіксації UTC: `[[ISO-8601 або UNKNOWN]]`
- SHA до переходу / tree SHA: `[[повні SHA або UNKNOWN]]`
- SHA після переходу / tree SHA: `[[повні SHA або UNKNOWN]]`
- Ідентифікатори станів архітектури: `[[підтверджені W0 ідентифікатори або UNKNOWN]]`
- Метод B0 — версія / SHA джерела / SHA конфігурації: `[[перевірені значення або UNKNOWN]]`
- Метод P — версія / SHA джерела / SHA конфігурації: `[[перевірені значення або UNKNOWN]]`
- Експозиція автора або знайомство зі сценарієм: `[[фактичний опис; не стверджувати blind holdout]]`

### Передумови та походження

| Перевірка | Статус | Артефакт і SHA-256 | Обмеження |
| --- | --- | --- | --- |
| W0 підтвердив послідовність станів і джерело | `[[PASS / UNKNOWN / BLOCKED]]` | `[[шлях, SHA-256 або UNKNOWN]]` | `[[факт або UNKNOWN]]` |
| Повнота target universe та джерел фактів | `[[PASS / UNKNOWN / BLOCKED]]` | `[[шлях, SHA-256 або UNKNOWN]]` | `[[факт або UNKNOWN]]` |
| Повний обов'язковий знаменник `Q(A_after)` | `[[COMPLETE / INCOMPLETE / UNKNOWN]]` | `[[шлях, SHA-256 або UNKNOWN]]` | `[[факт або UNKNOWN]]` |
| W2 evaluator і незалежне readback exact-pair доказів | `[[PASS / NOT_AVAILABLE / UNKNOWN]]` | `[[ID, source/tree/artifact/config SHA або UNKNOWN]]` | `[[факт або UNKNOWN]]` |
| Ізоляція input bundles | `[[PASS / FAIL / NOT_RUN]]` | `[[інвентар та SHA-256 або UNKNOWN]]` | `[[факт або UNKNOWN]]` |
| Source-to-image attestation | `[[VERIFIED / UNVERIFIED / UNKNOWN]]` | `[[digest або UNKNOWN]]` | `[[факт або UNKNOWN]]` |

## Виконання

| Метод | Run ID | Цільовий source SHA | Input bundle SHA-256 | Старт UTC | Статус запуску | Передбачення |
| --- | --- | --- | --- | --- | --- | --- |
| B0 | `[[значення або UNKNOWN]]` | `[[SHA або UNKNOWN]]` | `[[SHA або UNKNOWN]]` | `[[ISO-8601 або UNKNOWN]]` | `[[NOT_RUN / COMPLETED / FAILED / UNKNOWN]]` | `[[SEALED / NOT_EMITTED / UNKNOWN]]` |
| P | `[[значення або UNKNOWN]]` | `[[SHA або UNKNOWN]]` | `[[SHA або UNKNOWN]]` | `[[ISO-8601 або UNKNOWN]]` | `[[NOT_RUN / COMPLETED / FAILED / UNKNOWN]]` | `[[SEALED / NOT_EMITTED_GOVERNANCE_HOLD / UNKNOWN]]` |

- SHA sealed prediction B0: `[[SHA-256 або UNKNOWN]]`
- SHA sealed prediction P: `[[SHA-256 або UNKNOWN]]`
- Валідація кандидата P: `[[VALID / INVALID / UNKNOWN / NOT_RUN]]`
- Рішення governance P: `[[ACCEPT / REJECT / HOLD / UNKNOWN / NOT_RUN]]`
- Причини HOLD/UNKNOWN: `[[точні reason codes або UNKNOWN]]`

## RQ1 — ідентифікація впливу та коректність операцій

Статус: `[[NOT_EVALUABLE / SCORED / DIAGNOSTIC_ONLY]]`
Scorer викликано: `[[true / false]]`
Причина недоступності: `[[reason code або N/A]]`

| Метод | TP | FP-in | FP-extra | FN | TN | Precision | Recall | F1 | Точність операцій | Матриця операцій |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| B0 | `[[число/null]]` | `[[число/null]]` | `[[число/null]]` | `[[число/null]]` | `[[число/null]]` | `[[значення/null]]` | `[[значення/null]]` | `[[значення/null]]` | `[[значення/null]]` | `[[посилання або UNKNOWN]]` |
| P | `[[число/null]]` | `[[число/null]]` | `[[число/null]]` | `[[число/null]]` | `[[число/null]]` | `[[значення/null]]` | `[[значення/null]]` | `[[значення/null]]` | `[[значення/null]]` | `[[посилання або UNKNOWN]]` |

Не підмінюйте канонічний scorer порівнянням незасвідчених operation plans. Якщо P не створив sealed prediction, зазначте `NOT_EVALUABLE` і не заповнюйте метрики.

## RQ2 — валідне покриття обов'язків

- Статус знаменника: `[[COMPLETE / INCOMPLETE / UNKNOWN]]`
- Знаменник і його SHA-256: `[[перелік ID та digest або UNKNOWN]]`
- Кількість обов'язкових активних обов'язків: `[[число або UNKNOWN]]`
- Невирішені обов'язки: `[[перелік або UNKNOWN]]`

| Обов'язок | B0 evidence-backed | P candidate potential | P governance accepted | Exact-pair/evaluator evidence |
| --- | --- | --- | --- | --- |
| `[[ID або UNKNOWN]]` | `[[COVERED / DIAGNOSTIC_ONLY / UNKNOWN]]` | `[[COVERED / DIAGNOSTIC_ONLY / UNKNOWN]]` | `[[COVERED / DIAGNOSTIC_ONLY / UNKNOWN / ABSENT]]` | `[[артефакти, source SHA, SHA-256 або UNKNOWN]]` |

| Покриття | Відсоток |
| --- | ---: |
| B0 evidence-backed | `[[значення або UNKNOWN]]` |
| P candidate potential | `[[значення або UNKNOWN]]` |
| P governance accepted | `[[значення або UNKNOWN]]` |

`TEST_ONLY` доказ залишається діагностичним. Не рахуйте відсоток для неповного знаменника або невирішених точних пар; не прирівнюйте відсутню телеметрію до нульових порушень.

## RQ3 — витрати та час

- Timer boundary ID: `[[однаковий для обох методів або UNKNOWN]]`
- Порівнюваність: `[[DESCRIPTIVE / NOT_COMPARABLE / UNKNOWN]]`

| Метод | Адаптація, нс | Evaluator, нс | Перевірка, нс | Разом, нс | CPU, mCPU | RSS, байти | Джерело та image provenance |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| B0 | `[[число або UNKNOWN]]` | `[[число або UNKNOWN]]` | `[[число або UNKNOWN]]` | `[[число або UNKNOWN]]` | `[[число або NOT_COLLECTED]]` | `[[число або NOT_COLLECTED]]` | `[[attestation SHA або UNKNOWN]]` |
| P | `[[число або UNKNOWN]]` | `[[число або UNKNOWN]]` | `[[число або UNKNOWN]]` | `[[число або UNKNOWN]]` | `[[число або NOT_COLLECTED]]` | `[[число або NOT_COLLECTED]]` | `[[attestation SHA або UNKNOWN]]` |

Обмеження висновку: `[[один перехід є описовим; не робити висновку про статистичну значущість]]`.

## RQ4 — архітектурні контролі та governance

| Контроль | Статус | Source SHA | Evaluator / fixture SHA | Переглянуто елементів | Raw evidence SHA-256 | Висновок і обмеження |
| --- | --- | --- | --- | ---: | --- | --- |
| ΔA4 RETAIN-only негативний контроль | `[[PASS / FAIL / UNKNOWN / NOT_RUN]]` | `[[SHA або UNKNOWN]]` | `[[ID та SHA або UNKNOWN]]` | `[[число або UNKNOWN]]` | `[[digest або UNKNOWN]]` | `[[спостереження або UNKNOWN]]` |
| Заборонений cross-module import | `[[PASS / FAIL / UNKNOWN / NOT_RUN]]` | `[[SHA або UNKNOWN]]` | `[[ID та SHA або UNKNOWN]]` | `[[число або UNKNOWN]]` | `[[digest або UNKNOWN]]` | `[[спостереження або UNKNOWN]]` |
| Цикл залежностей | `[[PASS / FAIL / UNKNOWN / NOT_RUN]]` | `[[SHA або UNKNOWN]]` | `[[ID та SHA або UNKNOWN]]` | `[[число або UNKNOWN]]` | `[[digest або UNKNOWN]]` | `[[спостереження або UNKNOWN]]` |
| Порушення володіння даними | `[[PASS / FAIL / UNKNOWN / NOT_RUN]]` | `[[SHA або UNKNOWN]]` | `[[ID та SHA або UNKNOWN]]` | `[[число або UNKNOWN]]` | `[[digest або UNKNOWN]]` | `[[спостереження або UNKNOWN]]` |
| Помилка синхронного handler та rollback транзакції | `[[PASS / FAIL / UNKNOWN / NOT_RUN]]` | `[[SHA або UNKNOWN]]` | `[[ID та SHA або UNKNOWN]]` | `[[число або UNKNOWN]]` | `[[digest або UNKNOWN]]` | `[[PostgreSQL fixture та спостереження або UNKNOWN]]` |
| Governance P | `[[ACCEPT / REJECT / HOLD / UNKNOWN / NOT_RUN]]` | `[[SHA або UNKNOWN]]` | `[[трасування та digest або UNKNOWN]]` | `[[число або UNKNOWN]]` | `[[digest або UNKNOWN]]` | `[[причина або UNKNOWN]]` |

## Архів, відтворюваність та обмеження

- Evidence inventory SHA-256: `[[digest або UNKNOWN]]`
- ZIP archive SHA-256: `[[digest або UNKNOWN]]`
- SHA-256 sidecar: `[[шлях та digest або UNKNOWN]]`
- Читання після чистого розпакування: `[[PASS / FAIL / NOT_RUN / UNKNOWN]]`
- Повторення команд відтворення: `[[точні команди та фактичний результат]]`
- Невирішені залежності W0/W2: `[[перелік або NONE]]`
- Застереження щодо валідності та меж інтерпретації: `[[фактичні обмеження або UNKNOWN]]`

Не стверджуйте незалежність авторського референсу, production authority, G1/G4 готовність, статистичну значущість чи перевагу архітектури без окремих перевірених підстав.
