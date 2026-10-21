# DEV-B0P-V1 E1: evidence-sufficient калібраційна оцінка

- **Дата:** 21 жовтня 2026 року
- **Основний запуск:** `b0p-e1-cal-20261021-a4` (`EXECUTED_COMPLETE`)
- **Класифікація переходу:** `CALIBRATION_EXPOSED`
- **Дослідницькі шлюзи:** G1 `INCOMPLETE`; G4 `NOT AUTHORIZED`; `P_ALGORITHM_STATUS=NOT_READY`

## 1. Наукова задача та межа висновку

Порівнюється незмінна конфігурація B0 та заморожений Method P після переходу A0 → A0.1. Калібраційна гіпотеза: якщо Method P отримує source-pinned DEVELOPMENT факти, свіжі evaluator observations і точкові semantic controls, він зможе побудувати структурно валідного кандидата та сформувати операційний план, якого B0 із замороженою конфігурацією не має. Це не формальна пререєстрація загальної ефективності, а перевірка поведінки відомого калібраційного прикладу.

Цей запуск не є сліпим тестом: A0 → A0.1 і його цільові операції були оприлюднені та неодноразово розглядалися під час PILOT-02. E0 та E1 також відрізняються доступними доказами й припущеннями, тому їхня різниця не є рандомізованим або причинно ізольованим ефектом. Один архітектурний перехід не дає підстав для статистичної значущості чи узагальнення ефективності.

## 2. Умови E0 та E1

| Умова | Спостереження | Висновок запуску |
|---|---|---|
| E0 — evidence-poor | Незмінний історичний `dev-b0p-20261020-execution-a04`; B0 кандидат `VALID`, P кандидат `INVALID`, P не запропонував операцій і завершився `HOLD`. | RQ1 `NOT_EVALUABLE`; RQ2 `UNKNOWN`; точні пари не були незалежно перевірені. E0 та його архів не змінювалися. |
| E1 — evidence-sufficient DEVELOPMENT | Нові B0 і заморожений P запущені в окремих offline-контейнерах на тому самому A0 → A0.1. P отримав source-pinned факти, свіжі evaluator observations, підписаний TEST_ONLY sidecar та два TEST_ONLY контролі точних пар. | Обидві arm execution завершені. B0 запечатав прогноз; P створив валідного кандидата й план операцій, але governance залишив `HOLD`. |

E0 report: [B0P_DEVELOPMENT_REPORT.md](B0P_DEVELOPMENT_REPORT.md). Його архів E0 доступний як [dev-b0p-20261020-execution-a04.zip](https://github.com/user-attachments/files/33752991/dev-b0p-20261020-execution-a04.zip), SHA-256 `13f81c4f74e3cbbf857da204ecff3c22c6f86a87f4c0e0ee4c782983d416cc64`.

E0 не містив прив'язаного до запуску TEST_ONLY sidecar, нових source facts, свіжого inherited-evaluator bundle та двох звітів exact-pair semantic controls; E0 також не мав reference, придатного до canonical scoring. E1 додає ці DEVELOPMENT артефакти, але їхній TEST_ONLY trust scope не стає незалежною production authority.

## 3. Заморожені джерела та reference

| Джерело | SHA / статус |
|---|---|
| Base `main` до цієї роботи | `83aec475dcc00875faa2e4e0851064b23455f2cf` |
| E1 runner source revision | `14fc8b1bbec2aad2f2968e96e04a02b81a9ed720` |
| Архітектура до / після | `b78b0967be937634b7762baccf5ac6892b279a73` / `3fdd5c68f8f60fad5757eefa66cc2aa8b24d9306` |
| B0 source та політика | `165a7d6ef31adbe8ce3abe9f72e59d74692c987e` |
| Заморожений Method P source | `984f75b11b3153c52275e223ce8ec23b8d0dd0e5` |
| Підготовчий manifest E1 | `537ac6cace3a0ec916a881f81ee8875f7075d59948d8f2478c115de0caaed9df` |
| B0 / фактичний P input bundle | `62ce5f223715a35a407e58c92c45355ddd31708de192a0479e1afeb2f133b628` / `c6999dd1e2d6170ba16f2abe253fbb8c787f5379bc7973030f69252de8871ba8` |
| Reference status / SHA-256 | `AUTHOR_DECLARED_CALIBRATION_EXPOSED` / `74687534920eee5ea9782808be1557f9afc7f2f730be600d7884e7ecdcefa69c` |
| Новий inherited-evaluator run / source revision | `pilot02-inherited-e1cal-20261021-a5` / `14fc8b1bbec2aad2f2968e96e04a02b81a9ed720` |

Reference зафіксовано до виконання E1, перевірено за pinned Git-фактами та збережено поза P input. Його побудовано з оприлюдненого рядка ΔA1 у специфікації переходів, каталогу репрезентацій A0, публічного поля `required_obligations_after` сценарію DA01 та каталогу зобов'язань. Історичні виходи P не використовувалися як ground truth. Reference не є незалежним від історії розробки й не є holdout.

У P input не передавались reference operation labels, expected answers, scorer outputs, інший arm output або Git-історія. P запускався з `--network=none`; reference не монтувався до контейнера P. TEST_ONLY припущення й політичний набір залишилися development-only; production authority з них не випливає.

## 4. Рішення Method P та B0

| Результат | E0 | E1 |
|---|---|---|
| B0 | Кандидат `VALID`; sealed prediction SHA-256 `124a2495b5217d1686c9ddae631980c1c314654e8b12a9c48d4fc949deef9b34` | Та сама незмінна B0-конфігурація; prediction `SEALED` з тим самим SHA-256 |
| P candidate validation | `INVALID` | `VALID`; candidate config SHA-256 `63f4ed0f6105c703638174f83dabe54d713fa47a4f897de6de3f0fa6dcff29a0` |
| План P | Порожній | `ADD` для `AC_MODULE_STRUCTURE`; `REPLACE` для `REP_A0_ARCH_CI_LAYERING` |
| P prediction / governance | Prediction відсутній; `HOLD` | Prediction відсутній (`NOT_EMITTED_GOVERNANCE_HOLD`); `HOLD` |

E1 operation plan збігається з двома очікуваними операціями відкритого калібраційного reference; чотири performance/reliability репрезентації залишаються retain у reference. Це лише описове порівняння operation plan для відкритого переходу, без canonical RQ1 score. Воно збігається і з раніше оприлюдненим PILOT-02 V6 pattern, тому не є незалежним підтвердженням ефективності. Frozen Method P source не змінювався й не отримував правил для DA01 або відомих operation IDs.

Причини governance `HOLD`: `IMPACTED_RETAIN_REASSESSMENT_MISSING`, `INVARIANT_VERDICTS_NOT_ALL_POSITIVE`, `VERIFIED_GOVERNANCE_PIPELINE_PROOF_MISSING`. План операцій додатково містить `IMPACTED_RETAIN_REASSESSMENT_MISSING`. Валідність структури кандидата не означає прийняття або розгортання адаптації.

## 5. Незалежні від P перевірки точних пар

Для кожної пари перевірено source/configuration binding, scope, реальний evaluator run, stdout/stderr digests, перевірений позитивний випадок і контрольовану негативну мутацію. Перевірка виконана окремим PILOT-02 semantic-validation шляхом, а не зчитуванням semantic verdict з Method P.

| Репрезентація | Зобов'язання | Архітектура | Результат | Межа довіри |
|---|---|---|---|---|
| `REP_A01_ARCH_INTERNAL_LAYERING_CI` | `AC_LAYERING` | `3fdd5c68f8f60fad5757eefa66cc2aa8b24d9306` | `VERIFIED`, `VALID`; report SHA `f1486b9f01eef74a69a3e6369d61d1f06c627fbf46f25a0f3c7b6b7ba83f7075` | `TEST_ONLY` |
| `REP_A01_ARCH_MODULE_STRUCTURE_CI` | `AC_MODULE_STRUCTURE` | `3fdd5c68f8f60fad5757eefa66cc2aa8b24d9306` | `VERIFIED`, `VALID`; report SHA `d8d81ba47ba9337042a222896ca111d7760f832a404e55e50c45421a562afd9d` | `TEST_ONLY` |

Докази пари мають точний source SHA та окремі evaluator artifact digests `5e938273faa86b4584886e2ede5700b35b064d5e54fe04b0c3d1e50278c64eb0` і `d1f7ae29a1c8ed5fb5a4e1c37df8c8c22bfe98a31e0fa85c8c32012c0d083f7c`. Людської незалежної оцінки не проводилося. Ці два контролі не надають production authority і не перетворюють PILOT-02 на DA01 `Coverage_ref`.

## 6. RQ1 та RQ2

### RQ1

Canonical `score_rq1()` не викликався: P залишився в `HOLD` і не видав prediction. Офіційний результат — `NOT_EVALUABLE`; TP, FP, FN, TN, precision, recall, F1, operation accuracy та confusion matrix не обчислювалися. B0-only prediction не оцінювався самостійно. Описовий operation-plan match вище не є скорингом.

### RQ2

Однаковий повний знаменник — шість зобов'язань. Coverage percentage відсутній (`null`); фінальний статус `UNKNOWN`.

| Зобов'язання | B0 valid coverage | P candidate potential | P governance-accepted | Відсутній доказ |
|---|---|---|---|---|
| `P_EXT_LATENCY` | `UNKNOWN` | `UNKNOWN` | `ABSENT` | Немає валідної exact-pair семантичної перевірки для runtime/test latency |
| `R_BUSINESS_FAILURE` | `UNKNOWN` | `UNKNOWN` | `ABSENT` | Не вистачає валідної пари та runtime failure counter |
| `R_HTTP_5XX` | `UNKNOWN` | `UNKNOWN` | `ABSENT` | HTTP 5xx counter/знаменник відсутні, exact-pair доказу немає |
| `R_LOCAL_ATOMICITY` | `UNKNOWN` | `UNKNOWN` | `ABSENT` | Немає поточного точного доказу atomicity |
| `AC_LAYERING` | `UNKNOWN` | `DIAGNOSTIC_ONLY` | `ABSENT` | Пара `TEST_ONLY`; governance не прийняв адаптацію |
| `AC_MODULE_STRUCTURE` | `UNKNOWN` | `DIAGNOSTIC_ONLY` | `ABSENT` | Пара `TEST_ONLY`; governance не прийняв адаптацію |

Внутрішній candidate diagnostic P дорівнює 2/2 лише для його активного applicability subset. Це не шестипунктовий знаменник і не RQ2 coverage. Відсутні докази не рахувалися як нуль помилок або позитивне покриття.

## 7. Evaluators та витрати виконання

Новий inherited run `a5` має валідований EXP-01 bundle SHA `5ec0ed02bca1acc5924bc7da8cb183f3d917514d3903231e824dff0b8d235ed7`, representation evidence SHA `de65645d666c9a9b207c4d7c83e7f52caa77b761eda7baa5db9f1b0b72470b7e`, 61 запис у artifact inventory і validated evidence integrity.

- Locust: 131 запит, 0 невдалих, p50 `16 ms`, p95 `26 ms`, p99 `40 ms`, throughput `4.5999 req/s`. Це workload observation; поріг прийнятності не встановлювався, тож evaluator не присвоює compliance verdict.
- Інтеграційний тест `test_enabled_faults_delay_fail_deterministically_and_reset`: 1/1 пройшов, exit 0.
- Runtime HTTP histogram: записано інтервальні дельти bucket/count/sum; квантили з histogram buckets не обчислювалися.
- Runtime failures: HTTP 5xx series і business-operation failure counters відсутні; статус `UNKNOWN`, а не нуль.
- Source-to-image provenance: endpoint був стабільно прив'язаний до одного контейнера, але application revision не спостерігався, а authoritative source-to-image proof відсутній (`unverified`). Тому ці workload і runtime observations не доводять архітектурну adequacy чи production performance.

Додаткові E1 evaluators: frozen B0 Import Linter завершився з exit 1, але його evidence `VALID` і compliance `NOT_EVALUABLE`: один з чотирьох конфігурованих selectors (`app.repositories`) не існує в A0.1; це stale-scope mismatch, не підтверджена архітектурна помилка. `tests/architecture` завершився з exit 0 і 6/6 тестами; process-level compliance `COMPLIANT`, semantic adequacy `UNKNOWN`.

| Вимірювання E1 | Значення |
|---|---:|
| B0 container wall time | `580,301,250 ns` |
| P container wall time | `1,399,721,875 ns` |
| P adaptation timer | `306,113,458 ns` |
| E1 evaluator wall time | `578,193,875 ns` |
| Evidence-verification timer | `1,663,208 ns` |
| Host/container CPU та peak RSS | `UNKNOWN` |

У звіті E0 наведено окремі method-time значення B0 `70,372,750 ns` і P `410,543,750 ns`; ці timer boundaries відрізняються від E1 container wall time. Їх не трактовано як speedup або коректний порівняльний overhead. Повторні запуски одного переходу не є незалежними архітектурними зразками.

## 8. Результати за рівнями

- **Інженерний:** E1 повністю виконав B0 і заморожений P, зберіг відмову governance, перевірив підпис і digest TEST_ONLY inputs, незалежно перечитав дві точні пари та успішно пройшов clean-extraction readback. Основний E1 manifest містить 577 перевірених артефактів.
- **Методологічний:** на відміну від E0, у E1 P сформував `VALID` кандидата й два очікувані операційні діагнози після подачі додаткових доказів. Але авторитет цих припущень TEST_ONLY, governance лишився `HOLD`, а незалежно перевірені пари не дають повного знаменника. Це демонструє виконання pipeline та діагностичну чутливість на відомому переході, але не доводить, що якість адаптації зросла.
- **Науковий:** валідного RQ1 балу або RQ2 coverage не отримано. Наукова ефективність Method P не встановлена.

## 9. ΔA2 — здійсненність майбутнього переходу

ΔA2 (`A0_2_PUBLIC_MODULE_APIS`) технічно здійсненний як окремий DEVELOPMENT перехід, але не готовий до B0/P запуску. Поточні `app/modules/*/api.py` є FastAPI REST routers, не стабільними внутрішніми module contracts; явних public API модулів немає. Код напряму перетинає внутрішні межі: `tasks.service` імпортує `audit.service`, `notifications.service` і `users.repository`; `users.service` імпортує `audit.service`; `reporting.service` імпортує `tasks.service`. Наявний Import Linter конфігурує лише внутрішню шарову структуру модулів і не забороняє такі cross-module imports. У state manifest A0.1 `cross_module_public_api_enforcement` вимкнено.

Перед будь-яким запуском ΔA2 залишаються такі кроки:

1. Визначити й реалізувати публічний контракт кожного capability module та перенести поточні cross-module callers на ці контракти, зберігши один процес, синхронний виклик і одну БД.
2. Додати `AC_PUBLIC_API` до applicability/fitness contract і candidate templates; зафіксувати, які наявні зобов'язання лишаються активними.
3. Створити source-pinned evaluator та Import Linter rule з повним non-vacuous scope; перевірити clean case і контрольоване порушення (наприклад, прямий імпорт `notifications.repository`).
4. Зафіксувати source revision, evaluator/configuration digests, повний знаменник та очікуваний reference до першого запуску P. Попереднє знання сценарію ΔA2 задекларувати; не називати його blinded holdout без доказу ізоляції.
5. Перевірити evaluator outputs, exact-pair mapping, image identity/source binding і повноту runtime/performance/reliability evidence до B0/P execution.

У цій роботі ΔA2 не імплементувався і Method P на ньому не запускався.

## 10. Архів, відтворення та обмеження

Повний пакет містить E1 run archive і raw directory, fresh inherited evaluator run та EXP-01 artifacts, точний P input/sidecar, semantic controls, frozen reference, versioned protocols, E0 archive pointer і дві виключені невдалі readback спроби. E0 не перезаписувався й не дублювався у байтах.

- [Завантажити evidence package](DEV_B0P_E1_CALIBRATION_20261021.zip)
- [SHA-256 sidecar](DEV_B0P_E1_CALIBRATION_20261021.zip.sha256)
- Package SHA-256: `2cab9647921a294452b56c0320c831b3e8043b266bdde13d464f570231e65207`
- У пакеті 2,321 payload files; усі 2,322 записи `SHA256SUMS` (включно з package manifest), ZIP integrity, clean extraction і кожен manifest digest перевірено.
- Внутрішній E1 ZIP SHA-256: `c611bf7404a565a68c897095effeb798ee3fb36aef46346ba66ea6e487c43c9e`; незалежний readback після чистого extraction повернув `verified=true`, 577 artifacts, B0 `SEALED`, P `HOLD`, RQ1 `NOT_EVALUABLE`, RQ2 `UNKNOWN`.
- Fresh inherited evaluator integrity: `validated`, 61 artifacts.

### Перевірка коду

- `tests/unit/test_b0p_e1_execution.py`: **9 passed**.
- `make development-quality`: **PASS** — Ruff check/format (290 files), Mypy (121 source files), Bandit (warnings only), Import Linter (5 contracts kept, 0 broken), architecture tests (6 passed), migration validation passed, development regression (424 passed), EXP-01 (49 passed), EXP-02 (30 passed). Один наявний Starlette/httpx deprecation warning.
- Make target навмисно виключає `tests/unit/test_da01_execution.py` та `tests/unit/test_research_schema_foundation.py`; їх не рахували як пройдені.

Фокусований regression запуск:

```bash
PYTHONPATH=/Users/oleksii_makieiev/Documents/startups/evofit-bench \
PATH=/private/tmp/b0p-venv/bin:$PATH \
/private/tmp/b0p-venv/bin/pytest -q tests/unit/test_b0p_e1_execution.py
# 9 passed
```

Повторний E1 запуск відтворювався з чистого checkout SHA `14fc8b1bbec2aad2f2968e96e04a02b81a9ed720` командою:

```bash
PATH=/private/tmp/b0p-uv/bin:/private/tmp/b0p-venv/bin:$PATH \
PYTHONPATH=/private/tmp/evofit-b0p-e1-clean \
UV_PROJECT_ENVIRONMENT=/private/tmp/b0p-venv \
UV_CACHE_DIR=/private/tmp/b0p-uv-cache \
/private/tmp/b0p-venv/bin/python -m scripts.execute_b0p_e1 \
  --preparation-directory /private/tmp/evofit-b0p-e1-clean/experiments/results/b0p-e1-prep-cal-a4 \
  --p-method-input-directory /private/tmp/evofit-p-e1-prepared-a4/verified_method_input \
  --adaptation-evidence-sidecar /private/tmp/evofit-p-e1-prepared-a4/adaptation_evidence_test_only.json \
  --semantic-verification-directory /private/tmp/evofit-p02-semantic-e1-v2 \
  --reference /private/tmp/evofit-b0p-e1-clean/experiments/pilots/DEV_B0P_E1_REFERENCE_V1.json \
  --run-id b0p-e1-cal-20261021-a4 \
  --repository /private/tmp/evofit-b0p-e1-clean \
  --uv uv --docker docker
```

Локальний quality gate запускався на окремій disposable БД:

```bash
PATH=/private/tmp/b0p-uv/bin:$PATH \
UV_PROJECT_ENVIRONMENT=/private/tmp/b0p-venv \
UV_CACHE_DIR=/private/tmp/b0p-uv-cache \
TEST_DATABASE_URL=postgresql+psycopg://evofit:evofit@127.0.0.1:55439/evofit_test \
make development-quality
```

Локальна перевірка не є hosted CI. G1 лишається `INCOMPLETE`, G4 — `NOT AUTHORIZED`; жоден synthetic test, TEST_ONLY proof або зелений engineering check цього не змінює.
