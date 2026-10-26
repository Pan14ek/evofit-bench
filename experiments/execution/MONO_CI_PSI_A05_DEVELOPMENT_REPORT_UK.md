# DEVELOPMENT-звіт: перехід A0.4 → A0.5 і перевірка володіння даними

> **Актуальний висновок: PARTIAL.** Свіжий, outcome-neutral DEVELOPMENT-запуск підтвердив у задекларованій статичній області перевірки прогалину prospective A0.4 baseline: обидва старі контролі не виявили ін’єкцію, а окремий evaluator володіння даними виявив її. Method Ψ завершився `HOLD` із нульовою кількістю операцій, а candidate залишив `AC_DATA_OWNERSHIP` непокритим. Це інженерний DEVELOPMENT-доказ, а не успішна адаптація, виміряна наукова перевага чи схвалення експерименту.

## Актуальний запуск після P1-виправлень PR #56

Цей розділ описує новий запуск на виправленому коміті. Нижче збережено попередній звіт і його release як історичні дані; вони не є доказами нового запуску й не були перезаписані.

### Ідентичність виконання і відтворення probe

- PR: [#56](https://github.com/Pan14ek/evofit-bench/pull/56), база `2b4c64c7ad3ac335d31b53db0f88e4f39b1ed774`. Виправлення закомічено двома комітами: `5a343d590e523645b67db641dd3cf01c5cdec36a` і схема/тестове виправлення `87f7c7647e22768387b4f86bc5dcd9547e325f6f`.
- Свіже виконання: `DEV_PSI_TRANSITION_A05_FIX56_20261026_02`, `execution_origin=LOCAL`; джерело — committed A0.5 `87f7c7647e22768387b4f86bc5dcd9547e325f6f`, дерево репозиторію `feab833e1705a10aeed4028ec44e489aa3e4d591`, application tree `007196f68652bc13f6798805793ffdfae96f95f7`.
- Перехід: A0.4 `d3101c0d3aa9b7b709253b6ec7518416f05f65b9` (repository tree `2b436e0aaf09403ea516d73d20a466a122f86592`) → A0.5 `87f7c7647e22768387b4f86bc5dcd9547e325f6f`. Application tree не змінився.
- Probe є детерміновано відтвореним локальним комітом `e6a290d3a3d35dc295dffb8181873e1a1d3bc503`, parent — committed A0.5 `87f7c7647e22768387b4f86bc5dcd9547e325f6f`. Probe commit позначений `LOCAL_ONLY_RECREATED_FROM_PATCH`; його наявність у remote не потрібна.
- Probe змінив лише `app/modules/tasks/repository.py`. Parent repository/application trees: `feab833e1705a10aeed4028ec44e489aa3e4d591` / `007196f68652bc13f6798805793ffdfae96f95f7`; результат: `f3ea257bc97f50d646e0edcd54498a1d761216a1` / `5f0f8d9ebd4334556c583dabc300e5eb3db1900f`.
- Parent-file SHA-256 `6dbb8bd5ba5113476e948aadb3ac1bf7ee66c33c5dbd81bd37aca972a795c695`; modified-file SHA-256 `0cc63a811f0fcb5a110dace6f0c1b928764b0f6f6dcbe2a605fb4eb19ae5e61c`; patch SHA-256 `ca614f99c800cd16feea7d18c6344a8f326570b3677801c4ac2d8499d9be65cd`; probe-manifest SHA-256 `9caeaf8a74645fdc21164ddc5ccdd5484fbbee36ee87c3ce8f55fcfc0f060d82`.
- `replay-probe` відтворив ідентичний commit/tree із run directory, з extracted archive та з downloaded private-release asset — усі три readback-и `PASS`; кожен підтвердив modified source bytes і відсутність потреби у remote probe commit.

### Свіжі evaluator outcomes та інтерпретація

| Evaluator | Raw result на probe | Coverage | Detection |
|---|---|---|---|
| `AC_PUBLIC_API` | `COMPLIANT`, без finding | `COMPLETE`, exit 0 | `NOT_DETECTED` |
| `AC_MODULE_GRAPH` | `COMPLIANT`, без finding | `COMPLETE`, exit 0 | `NOT_DETECTED` |
| `AC_DATA_OWNERSHIP` | `NON_COMPLIANT`, `FOREIGN_TABLE_ACCESS` | `COMPLETE`, exit 1 | `DETECTED` |

Позитивний A0.5 запуск `AC_DATA_OWNERSHIP` — `COMPLIANT / COMPLETE`, exit 0. Сукупна класифікація старих контролів — `NOT_DETECTED`; case-level результат — `OLD_BASELINE_GAP_SUPPORTED`. Окремий загальний adequacy status лишився `NOT_EVALUABLE`, оскільки applicability та governance входів не встановлені. Це не скасовує узгоджений із raw output source-level detection result і не перетворює його на схвалений науковий висновок.

### Method Ψ, candidate і governance

- Method input bundle SHA-256: `ea8a450affdc6d073df05c4e7e67297bf25d2a72df7a47ef57f7459b145dd244`; raw result SHA-256: `57481cfbede5bd66e861af4f167306e9eb9d76bcbe01aa0d2f983339fbd3f76d`.
- Фактичний decision — `HOLD`; operation plan — `[]`; prediction відсутній. Причини: `COST_MODEL_UNRESOLVED`, `MANDATORY_APPLICABILITY_UNKNOWN`, `UNKNOWN_MANDATORY_LINK_PREVENTS_TRANSITION`.
- Candidate `0b23b4899a9c9c44d31fb773eedbcaa68cdc6331e53b3b0b2e3b54fdc6dd800a`, його method validation — `valid`, незалежний candidate readback — `PASS`. Два активні представлення залишилися незмінними (`AC_MODULE_GRAPH`, `AC_PUBLIC_API`); `AC_DATA_OWNERSHIP` має `NOT_COVERED`, жодної нової репрезентації немає. Governance — `HOLD`, cost verdict — `UNKNOWN`.
- Межі залишилися: `NO_GO`, `measurement=NOT_EXECUTED`, `P_ALGORITHM_STATUS=NOT_READY`, G1 `INCOMPLETE`, G4 `NOT_AUTHORIZED`, reference gate `NOT_READY`, scoring `NOT_EXECUTED`.

### Архів, локальний release fallback і CI

- DEVELOPMENT execution directory: `/private/tmp/evofit-pr56-fresh-run`. Архів: [локальний DEVELOPMENT prerelease](https://github.com/Pan14ek/evofit-bench/releases/tag/mono-ci-psi-a05-local-fix56-20261026-02), assets `evofit-pr56-development-a05-fix56.zip` і `.zip.sha256`.
- Походження явно `LOCAL`, workflow URL — `LOCAL_EXECUTION_NO_WORKFLOW`; архів має 500 members, SHA-256 `6abc5043e039522d68e1befd3d54b0376e2d9d1f7b620afb8a54cdfc4a5764ea`. ZIP integrity, detached sidecar, усі member digests, V4 transition verification, source replay і завантажений prerelease readback — `PASS`. Архів не позначений як створений GitHub Actions.
- Для PR head `87f7c7647e22768387b4f86bc5dcd9547e325f6f` GitHub запустив A0.5 run [40395770007](https://github.com/Pan14ek/evofit-bench/actions/runs/40395770007) і quality runs [40395769978](https://github.com/Pan14ek/evofit-bench/actions/runs/40395769978), [40395776758](https://github.com/Pan14ek/evofit-bench/actions/runs/40395776758). Усі jobs завершилися з `failure` та `steps: []`: **`BLOCKED_BEFORE_STEPS`**. Жоден hosted test не заявляється як виконаний.
- Через відсутність hosted artifact використано новий private prerelease fallback; попередній prerelease `mono-ci-psi-a05-40384246740-1` не змінювався.

### Перевірки на фінальному коміті джерела

- `make test-mono-ci-psi-a05` — `PASS`, 100 тестів.
- `make test-mono-ci-psi-transition` — `PASS`, 50 тестів; попередні V1/V2/V3 transition/archive контракти лишилися сумісними.
- `make test-mono-ci-b0-psi-execution` — `PASS`, 40 тестів; readiness залишається `NO_GO`, B0/Ψ і вимірювання — `NOT_EXECUTED`.
- `make development-quality` — `PASS` на `87f7c76`. Ruff check/format, Mypy (158 source files), Bandit, architecture/import checks, A0.1–A0.5 stage acceptance, migrations на окремій disposable PostgreSQL 16, regression (540 passed), EXP-01 (49 passed), EXP-02 (30 passed). Є один наявний Starlette/httpx deprecation warning.
- PostgreSQL quality database: ephemeral container `evofit-pr56-quality-20261026`, image `postgres:16` (`sha256:c319f2a8182bcdcbb3297d568e2a9cc9e7da3a624438e14b63921c719817e1b6`), database `evofit_pr56_quality`, loopback port `5439`; видалений після перевірки.
- Окремо `make lint`, `make development-typecheck` і `make security` пройшли; security tool виводив informational warnings. `git diff --check` — `PASS` для оновленого звіту.

Gap залишається підтриманим у межах цього prospectively reconstructed baseline та повністю заявленої static source scope. Це незалежно від того, що Method Ψ не адаптував candidate: Ψ — `HOLD`, операцій немає, ownership coverage не з’явилося. Вимога A0.5 лишається задекларованою інженерною політикою без незалежної normative approval; evaluator не доводить raw-SQL, reflection/dynamic, runtime-access чи database-permission enforcement. Жоден дослідницький gate не просунуто, frozen protocol/oracle/scorer не змінювалися.

## Попередній запуск до P1-виправлень (історичний)

## Ідентичність і походження

- PR: [#56](https://github.com/Pan14ek/evofit-bench/pull/56), база `2b4c64c7ad3ac335d31b53db0f88e4f39b1ed774`.
- DEVELOPMENT execution: `DEV_PSI_TRANSITION_A05_FINAL_04`, режим `DEVELOPMENT_METHOD_EXECUTION_ONLY`; source revision `d0be79a5a89e6a84e8b2b09307b0998b11681ac9` був HEAD PR під час запуску.
- Порівнюваний перехід: A0.4 `d3101c0d3aa9b7b709253b6ec7518416f05f65b9` → A0.5 `d0be79a5a89e6a84e8b2b09307b0998b11681ac9`.
- Дерево репозиторію: A0.4 `2b436e0aaf09403ea516d73d20a466a122f86592` → A0.5 `8407b2d29fbe844ac64662642a41b61f6b725de6`. Дерево application code в обох станах однакове: `007196f68652bc13f6798805793ffdfae96f95f7`; прикладний код не змінювався.
- DEVELOPMENT Method Ψ workflow [40384246740](https://github.com/Pan14ek/evofit-bench/actions/runs/40384246740) завершився до першого кроку: job має `steps: []`. GitHub не запустив runner через обмеження оплати/ліміту витрат. Тому фактичне виконання, формування архіву та readback виконані локально в ізольованому DEVELOPMENT-контурі; workflow URL — лише ідентифікатор запитаного запуску.
- Приватний [prerelease з архівом](https://github.com/Pan14ek/evofit-bench/releases/tag/mono-ci-psi-a05-40384246740-1), створений дозволеним fallback: `mono-ci-psi-a05-40384246740-1.zip`, SHA-256 `690e009783179d0af7f7cac3f0205f48ea2a11030eb5f2f8afa00685d06d2083`. Завантажений asset і detached checksum перевірено; `transition-verify` та readback дали `PASS`, 493 учасники архіву.
- Method input bundle SHA-256: `90385dcc5c5e9a88a83a38d3b10a483e51b95c437d0215a2636f1e41c582684a`; raw Ψ result SHA-256: `41f0cdcfd3ca16997817675cd152f14343f9f3e12e74177f4df1287bb8e6f4cc`.

## Що саме перевірялося

A0.5 manifest декларує `architecture.data_ownership.persistence_ownership`: таблиці `users`, `tasks`, `notifications` та `audit_events` мають власників-модулі; `app/db/model_registry.py` має вузький явно описаний виняток; reporting tables не мають власника (`NONE`). Це версійована інженерна вимога з `architecture/states/A0_5_MODULE_DATA_OWNERSHIP.yaml`, а не незалежно схвалена нормативна authority.

Prospective реконструкція A0.4 baseline (`MONO_CI_RECONSTRUCTED_B0_A04_V1`, `NOT_APPROVED`, `PROSPECTIVE_RECONSTRUCTION_NOT_HISTORICAL`) містить два активні представлення: `AC_PUBLIC_API` і `AC_MODULE_GRAPH`. `AC_DATA_OWNERSHIP` доступний як окремий evaluator, але не був доданий у цю базову конфігурацію.

Свіжі оцінювачі дали `COMPLIANT` на A0.4 і A0.5 для двох наявних контролів. Окремий evaluator володіння даними завершив позитивну перевірку A0.5 як `COMPLIANT` / `COMPLETE`. На ізольованому probe-коміті `7b8d7bfc53a9209d674ad3bdd22f1995255c75e4` змінено лише `app/modules/tasks/repository.py`, додавши звернення до чужої таблиці `notifications`: `AC_DATA_OWNERSHIP` повернув `NON_COMPLIANT`, finding `FOREIGN_TABLE_ACCESS`; `AC_MODULE_GRAPH` і `AC_PUBLIC_API` лишилися `COMPLIANT`. Отже, цей probe показує конкретну різницю у заявленому статичному scope evaluator-ів, а не загальну runtime-гарантію.

Діагностика зафіксувала, що два старі контролі не виявили probe, ownership evaluator виявив його, а reconstructed baseline недостатній для перевірки задекларованого обов’язку. Водночас applicability A0.5 лишилася `UNKNOWN`: policy authority не верифікована, registry має статус `OPEN`, посилання на charter/registry невирішені. Повнота та семантична достатність ownership evaluator не схвалені незалежно. Його відомі межі включають raw SQL, динамічний вибір таблиць, reflection, runtime access і database permissions.

## Фактичний результат Ψ і candidate readback

Method Ψ завершився `HOLD`; operation plan містить 0 операцій; prediction відсутній; scoring — `NOT_EXECUTED`. Причини включають невизначену applicability і mandatory classification, невирішену cost model, невстановлену повноту/authority входів та відсутність верифікованого доказу governance pipeline. Кандидат при цьому був виданий і пройшов незалежний source/configuration readback.

Candidate має SHA-256 `d1a1ff627e8e4ba77f97e0497893c17da126b494a0e880374e7b1e435cad5c47`; його дві активні репрезентації — ті самі `AC_MODULE_GRAPH` і `AC_PUBLIC_API`. Незалежна перевірка candidate — `PASS`: їхні джерело, конфігурації та outcomes були перевірені на позитивному й негативному джерелах і збіглися з reconstructed B0. Це підтверджує readback цих двох контролів, але не adequacy кандидата: `AC_DATA_OWNERSHIP` має `NOT_COVERED`, жодної нової репрезентації немає. Статус `PASS` не є доказом успішної адаптації.

У runtime A0.5 залишилися незмінними наявні архітектурні інваріанти: один deployable application process, одна PostgreSQL database, синхронні виклики, без broker. Порушення інваріантів не вводилися для одержання бажаного результату.

Оціночна вартість нових активних репрезентацій: `0` на CI build, оскільки candidate не додає controls. Виміряні одиничні subprocess wall-clock samples candidate на позитивному джерелі сумарно `237.418 ms`, на негативному — `261.338 ms`, загалом `498.756 ms`. Це один запуск, не benchmark або висновок про продуктивність.

## Перевірки та відтворення

- `make test-mono-ci-psi-a05` — `PASS`, 93 тести. Архівні regressions — `PASS`, 2 тести (25 deselected): `uv run --frozen --extra dev python -m pytest -q --no-cov -p no:cacheprovider tests/unit/test_mono_ci_psi_transition.py -k 'archive_metadata_accepts_a05_namespace_and_preserves_transition_names or a05_archive_schema_pins_the_prospective_a04_baseline'`.
- `make lint` — `PASS`.
- `make development-typecheck` — `PASS`, 158 source files.
- `make security` — Bandit пройшов; лише наявні informational warnings. Це не повний quality gate.
- Локальний archive pack, checksum, transition verification, завантаження prerelease asset і повторний readback — `PASS`, 493 учасники.
- Hosted quality/archive job — `BLOCKED_BEFORE_STEPS` через GitHub billing/spending-limit стан; жодного hosted test або `make development-quality` результату не заявляємо. `make development-quality` локально не запускали, бо він потребує окремої disposable PostgreSQL database.

Requirement-to-test traceability міститься у `tests/architecture/a1/REQUIREMENT_TEST_MATRIX.md`; targeted A0.5 тести та schema regressions перевіряють positive/negative ownership behavior, stage acceptance, transition data binding, candidate verification і archive сумісність.

## Наукові межі та висновок

Статус цього результату — **PARTIAL**: evidence встановлює gap між двома prospective A0.4 controls і задекларованою A0.5 вимогою, але Ψ не видав необхідну ownership adaptation і не зміг валідовувати її як покриту. Це не свідчить, що історичний A0.4 baseline мав ту саму конфігурацію, що normative вимога схвалена, або що Method Ψ кращий за baseline.

`study_readiness=NO_GO`, `measurement_status=NOT_EXECUTED`, `P_ALGORITHM_STATUS=NOT_READY`, G1 `INCOMPLETE`, G4 `NOT_AUTHORIZED`, reference gate `NOT_READY`; metrics `NOT_MEASURED`, scoring `NOT_EXECUTED`. DA01 ground truth, oracle, scorer, frozen source/protocol, sealed predictions і criteria не читалися як inputs та не змінювалися. Жоден research gate не просунуто.

Наступна межа — незалежно визначити applicability/mandatory classification та policy authority, довести повноту й семантичну достатність evaluator-ів, вирішити governance/cost blockers і лише окремим уповноваженим кроком переглядати готовність до вимірювання. Цей DEVELOPMENT-запуск не авторизує DA01 або інший офіційний measured comparison.
