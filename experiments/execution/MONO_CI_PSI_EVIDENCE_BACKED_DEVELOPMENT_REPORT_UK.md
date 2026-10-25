# Діагностичний звіт: evidence-backed Method Ψ на переході A0.3 → A0.4

> **Статус:** DEVELOPMENT-only технічний запуск і перевірка архіву. Це не виміряний експеримент, не оцінка якості адаптації та не наукове схвалення.

## Ідентичність запуску

- Репозиторій: `Pan14ek/evofit-bench`
- Гілка: `codex/psi-evidence-backed-adaptation`
- База PR: `main` на `bfe19ac68a4a11ca6d2eba5aa6a9cc202c805d31`
- Код запуску: `644b00cf35e8375d36e16e5f4da4a5db0bcfabea`
- Ідентифікатор: `DEV_PSI_TRANSITION_GHA_40194197616_1`
- CI: [GitHub Actions run 40194197616](https://github.com/Pan14ek/evofit-bench/actions/runs/40194197616)
- Точна пара джерел: A0.3 `26a9bb667da7d0938e38aca15d2bf29fd1de4829` → A0.4 `d3101c0d3aa9b7b709253b6ec7518416f05f65b9`
- Архів: [приватний prerelease з DEVELOPMENT-архівом](https://github.com/Pan14ek/evofit-bench/releases/tag/mono-ci-psi-transition-40194197616-1)
- SHA-256 архіву: `cbe1f067f4b030e04bc26bfe6e7cd9c40c2145783dbe1be9cfbbdf5b05dba5f6`
- Readback: `PASS`, 440 учасників архіву; завантажений архів повторно пройшов перевірку detached SHA-256 та `transition-verify`.

## Фактичне спостереження

Обидва закріплені A1-оцінювачі запущені як свіжі процеси на обох точних ревізіях. Усі чотири запуски завершилися з кодом 0 та повернули `COMPLIANT`:

| Стан | Оцінювач | Виконання | Результат оцінювача |
|---|---|---|---|
| A0.3 | `AC_PUBLIC_API` | `COMPLETED` | `COMPLIANT` |
| A0.3 | `AC_MODULE_GRAPH` | `COMPLETED` | `COMPLIANT` |
| A0.4 | `AC_PUBLIC_API` | `COMPLETED` | `COMPLIANT` |
| A0.4 | `AC_MODULE_GRAPH` | `COMPLETED` | `COMPLIANT` |

Для кожного raw output архів містить окремий типізований scope-файл, зв’язаний хешами з виходом оцінювача та `source_scope`: `AC_PUBLIC_API` охоплює 31 файл, `AC_MODULE_GRAPH` — 5 dependency edges в обох станах. Виходи оцінювачів дають технічні результати відповідності; вони не доводять, що representation достатньо вимірює нормативний обов’язок.

Ψ виконано за контрактом `MONO_CI_PSI_METHOD_RESULT_V2`. Фактичне рішення — `HOLD`; план операцій створено, але він містить **0 операцій**. Prediction і candidate не видані. Дві поточні пари (`AC_MODULE_GRAPH`, `AC_PUBLIC_API`) мають `compliance_status=COMPLIANT`, але їхній статус залишається `UNKNOWN`: семантичний доказ `UNDETERMINED`, достатність оцінювача не доведена, нормативне зіставлення не схвалено. Applicability і candidate coverage для всіх 18 зобов’язань залишилися `UNKNOWN`.

Причини `HOLD` включають невизначену applicability та класифікацію обов’язків, невирішену модель вартості, непідтверджену повноту/авторитетність входів і відсутність верифікованого доказу governance pipeline. Це обмеження доказів і повноважень, а не висновок про виміряний виграш або регресію адаптації.

## Порівняння з PR #53

У попередньому readback PR [#53](https://github.com/Pan14ek/evofit-bench/pull/53), run [40180285332](https://github.com/Pan14ek/evofit-bench/actions/runs/40180285332), архів `mono-ci-psi-transition-40180285332-1` (`47e1639b6b1fb250d524ca899bc14b0e7d96adc45e246c4bfa786854dab23a5b`) пройшов перевірку, але був контрактом V1 і не мав спостережень оцінювачів: 18 applicability-станів та 18 coverage-станів були `UNKNOWN`, операцій і prediction не було, рішення — `HOLD`.

Поточний запуск додає чотири нові спостереження A1 на A0.3/A0.4 і digest-bound typed inspection scopes. Це дозволило зафіксувати `COMPLIANT` від оцінювачів для двох поточних пар окремо від їхньої невирішеної семантичної валідності. Рішення governance лишилося `HOLD`; операцій і prediction немає. Отже, це приріст перевірюваного технічного evidence, а не доказ користі Method Ψ.

## Перевірки

- Hosted `make development-quality`: `PASS` у run [40194197633](https://github.com/Pan14ek/evofit-bench/actions/runs/40194197633); той самий gate також пройшов у transition workflow.
- Hosted `make test-mono-ci-b0-psi-execution`: `PASS`; 40 тестів.
- Hosted `make test-mono-ci-psi-transition`: `PASS`, включно з ізольованим реальним переходом та readback.
- Локальні `make development-lint`, `make development-typecheck`, `tests/unit/test_mono_ci_psi_evidence.py` (6 тестів), `tests/unit/test_context_documents.py`, перевірка JSON-схем і `git diff --check`: `PASS`.
- Локальний `make test-mono-ci-psi-transition` не зміг пройти sandbox setup: macOS повернув `sandbox-exec: sandbox_apply: Operation not permitted`. Офіційно використовувати ізоляцію без sandbox не стали; повний integration path пройшов у Linux CI з bubblewrap.
- Upload до GitHub Actions artifact storage не вдався через вичерпання storage quota. Workflow зберіг архів у приватному prerelease, завантажив його назад і перевірив checksum та витягнутий readback; незалежна локальна перевірка цього самого архіву також дала `PASS`.

## Незмінні наукові межі

- Режим довіри sidecar — `TEST_ONLY`; правила пілота залишаються `DRAFT`/`OPEN`.
- Базова конфігурація — `PROSPECTIVE_RECONSTRUCTION_NOT_HISTORICAL`, `NOT_APPROVED`; вона не була дозволена як офіційний Method P input.
- `P_ALGORITHM_STATUS=NOT_READY`, `G1=INCOMPLETE`, `G4=NOT_AUTHORIZED`, reference gate `NOT_READY`, study readiness `NO_GO`.
- Метрики `NOT_MEASURED`, scoring `NOT_EXECUTED`; цей запуск не порівнює B0 і Ψ та не створює наукового результату.
- Ground truth, scorer, sealed predictions, frozen protocols і критерії не змінювалися та не використовувалися як входи методу.

Наступна межа залишається окремим переглядом і авторизацією: визначити історично коректну базову конфігурацію, затвердити applicability/mandatory denominator і незалежну semantic adequacy, виконати G1/G4 та reference gate, після чого окремо вирішувати питання вимірюваного запуску.
