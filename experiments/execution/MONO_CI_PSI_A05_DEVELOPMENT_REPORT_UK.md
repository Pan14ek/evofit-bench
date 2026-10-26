# DEVELOPMENT-звіт: перехід A0.4 → A0.5 і перевірка володіння даними

> **Висновок: PARTIAL.** Встановлено прогалину в покритті задекларованого обов’язку у prospective A0.4 baseline. Метод Ψ завершився `HOLD`; перевірений ним candidate не додає контролю володіння даними. Це технічна DEVELOPMENT-діагностика, а не виміряний науковий результат, оцінка переваги чи схвалення адаптації.

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
