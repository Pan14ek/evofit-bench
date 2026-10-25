# Діагностичний звіт: покриття fitness та потреба в адаптації A0.3 → A0.4

> **Статус:** відтворюваний DEVELOPMENT-запуск і джерельно обмежена діагностика. `RETAIN_CANDIDATE` не є формальним схваленням, а `COMPLIANT` не доводить повну семантичну достатність representation.

## Ідентичність і збереження доказів

- База PR: `main` `9cd4d3560c3cc32e38ecfccfd834a5f15a06055d`; код запуску: `b42c33fa10c07164556fa52db9ab9bcd1dbce6a4`.
- Перехід: A0.3 `26a9bb667da7d0938e38aca15d2bf29fd1de4829` (`7b951421395f532ca403dab09d76902ff08a807d`) → A0.4 `d3101c0d3aa9b7b709253b6ec7518416f05f65b9` (`2b436e0aaf09403ea516d73d20a466a122f86592`).
- Виконання: `DEV_PSI_TRANSITION_GHA_40236384716_1`, режим `DEVELOPMENT_METHOD_EXECUTION_ONLY`; [успішний GitHub Actions run](https://github.com/Pan14ek/evofit-bench/actions/runs/40236384716).
- [Приватний prerelease з архівом](https://github.com/Pan14ek/evofit-bench/releases/tag/mono-ci-psi-transition-40236384716-1); SHA-256 `318f3ead9c8aaf208641cb866e689e034c4a86b56c0b9dffc1ef9ed7d8d3f273`. SHA-256 збігся з release sidecar; завантажений архів повторно пройшов `transition-verify` (`PASS`, 445 учасників). Actions artifact storage не прийняв файл, тому workflow зберіг його у приватному prerelease; попередні releases не перезаписувалися.

## Очікувані та перевірені предмети інспекції

Незалежний verifier побудував очікувану множину з точного Git tree, state manifest та evaluator `source_scope`; фактичну множину взяв із digest-bound evaluator output і перевірив хеші джерел. Для кожного з чотирьох запусків `expected_subjects == inspected_subjects`:

```text
audit/{__init__,model,public,repository,service}.py
notifications/{__init__,api,model,public,repository,schemas,service}.py
reporting/{__init__,api,public,schemas,service}.py
tasks/{__init__,api,model,public,repository,schemas,service}.py
users/{__init__,api,model,public,repository,schemas,service}.py
```

Шляхи в блоці відносні до `app/modules/`; разом це 31 файл для кожного evaluator і стану. Для `AC_PUBLIC_API` кожна з чотирьох перевірок дала `expected=31`, `inspected=31`, `missing=0`, `unexpected=0`, `altered=0`, `verified_matching=31`; статус — `COMPLETE_FOR_DECLARED_STATIC_SOURCE_SCOPE`. Для `AC_MODULE_GRAPH` облік файлів такий самий; статус — `STATIC_SCOPE_MATCHED_DYNAMIC_EDGE_COMPLETENESS_UNKNOWN`. Повні списки, хеші й джерела лежать у чотирьох `PSI/evaluator-observations/{before,after}/<control>/inspection-coverage.json` в архіві.

Для графа verifier окремо вивів з коду статичні import relationships: 6 до переходу й 7 після; обидва набори збіглися з фактичними спостереженнями (`MATCHED`). П’ять module-level edge subjects в обох станах: `reporting→tasks`, `tasks→audit`, `tasks→notifications`, `tasks→users`, `users→audit`; статичних циклів немає. Ці дозволені policy edges не використовувалися як очікувані фактичні імпорти. Перевірка графа також застосовує strict local import root `app`, облік shared-infrastructure roots, циклів та unresolved imports. У цьому статичному контракті conditional imports рахуються як edges, але star-import symbols невідомі; composition roots поза `app/modules` не є graph vertices. Повнота динамічних імпортів, reflection та runtime dependency injection залишається `UNKNOWN`.

## Що змінилося між станами

- `app/modules/reporting/service.py` змінив імпорт `task_summary` з `app.modules.tasks.service` на `TaskSummary` і `get_task_summary` з `app.modules.tasks.public`. Це заміна одного приватного source relationship двома public-interface imports; функціональний контракт звіту збережено за маніфестом A0.4.
- У A0.3 manifest тимчасовий виняток `reporting_tasks_query_intermediate_v1` дозволяв приватний імпорт у станах A0.2/A0.3 і вказував завершення на A0.4. У A0.4 manifest винятків немає, а заборонено саме `reporting.service → tasks.service.task_summary`.
- Дозволені п’ять module-level напрямків і всі задекларовані топологічні інваріанти не змінилися: один процес і deployment unit, одна PostgreSQL база, синхронні виклики, без broker, REST поведінка та caller-managed session.
- `AC_PUBLIC_API` evaluator configuration залишився тим самим (SHA-256 `8853c3a933b23f698c7ba7c5b6e511f292e8d9285dc0de4378741c53e466f7bb`), як і `AC_MODULE_GRAPH` configuration (SHA-256 `1abae6871a477ff2a07685ad645a70defa2f1ac6745598ae4cdc35aab4e95bf6`); evaluator source SHA також однаковий для всіх запусків (`5c17373ba8896ef0c443d826bd0064168ec7c5759c7973f9602b6c2c715b169c`). Обидва evaluator конфіги активні для A0.3 та A0.4. Отже, байти evaluator-конфігурації не редагувалися: A0.4 state усуває застосовність старого винятку, а задекларований public query port відповідає незміненому набору public exports.

## Висновок за кожним control

| Control / попередня representation | Спостереження та зміна вимоги | Діагностика потреби в зміні конфігурації |
|---|---|---|
| `AC_PUBLIC_API` / `REP_RECON_B0_A03_PUBLIC_API_CI_V1`; evaluator `1.0.0` | A0.3 і A0.4: по 31/31 файлів, `COMPLIANT`. Конфігурація перевіряє п’ять public modules, оголошені API names та поля `tasks.TaskSummary`; виняток для приватного `task_summary` обмежений A0.2/A0.3. На A0.4 source вже використовує Tasks public query; evaluator не дозволяє продовжити старий виняток у цьому стані. Runtime re-export і callable signatures не перевіряються. | `RETAIN_CANDIDATE`; `configuration_change_necessity=NOT_DEMONSTRATED_WITHIN_VERIFIED_SCOPE`. Технічні дані підтримують подальше використання на перевіреному A0.4 scope. Вони не закривають семантичну валідність пари або нормативне схвалення. `ADD`/`REPLACE` не обґрунтовані. |
| `AC_MODULE_GRAPH` / `REP_RECON_B0_A03_MODULE_GRAPH_CI_V1`; evaluator `1.0.0` | A0.3 і A0.4: по 31/31 файлів, `COMPLIANT`; 5 дозволених і спостережених module-level edges, без циклів. Source relationships змінилися з 6 на 7 через перехід Reporting на public API; module-level graph та правило не змінилися. Динамічну повноту не доведено. Конфігурація також перевіряє strict local imports, unresolved imports та cycles. | `RETAIN_CANDIDATE`; `configuration_change_necessity=NOT_DEMONSTRATED_WITHIN_VERIFIED_SCOPE`. Графова конфігурація покриває перевірений статичний scope, але невідомі динамічні залежності й семантична достатність. `ADD`/`REPLACE` не обґрунтовані. |

Для обох пар `pair_semantic_validity=UNKNOWN`. Залишаються відсутні докази: історична ідентичність baseline, незалежна перевірка семантики пар, незалежний review і схвалена нормативна applicability. Тому можна обґрунтувати лише технічний `RETAIN_CANDIDATE`, не фінальне `RETAIN`. Зміна архітектури сама по собі не доводить потребу в `ADD` чи `REPLACE`.

## Фактичний результат Method Ψ і межі висновку

- Method Ψ виконався на свіжих A0.4 observations; адаптаційна діагностика збережена окремо й не входила до `PSI/method-input/method_input_v3.json`.
- Реальний governance результат — `HOLD`; operation plan містить **0 операцій**, prediction не видано, scoring не виконувався. Candidate serialization пройшла validation (`valid`) без змін (`changes=[]`), але не була прийнята governance.
- `HOLD` зумовлений невідомою applicability та mandatory-класифікацією, невирішеною моделлю вартості, невизначеною повнотою/авторитетністю входів, не всіма позитивними invariant verdicts і відсутнім доказом governance pipeline. Усі 18 applicability залишилися `UNKNOWN`.
- Baseline лишається `PROSPECTIVE_RECONSTRUCTION_NOT_HISTORICAL`, `NOT_APPROVED`; policy залишається `DRAFT_NOT_APPROVED`/`OPEN` (у run metadata: `DRAFT_OPEN_UNAPPROVED`); trust scope — `TEST_ONLY`. Збережено `NO_GO`, `P_ALGORITHM_STATUS=NOT_READY`, `G1=INCOMPLETE`, `G4=NOT_AUTHORIZED`, `G-A1-C4-REF-FROZEN=NOT_READY`. Це не виміряний B0/Ψ comparison.

**На це питання перехід відповідає як retention/control case:** на перевіреному статичному source scope технічні докази підтримують використання наявних representations без продемонстрованої зміни конфігурації. Перехід не демонструє позитивної потреби в адаптації, але й не доводить формальну семантичну достатність чи схвалення `RETAIN`.

**Рекомендація B:** не використовувати цей перехід як доказ позитивної адаптації. Для наступного дослідження окремо визначити й зафіксувати перспективний реалістичний перехід, який може спростувати чинну representation; до виміряного B0/Ψ порівняння окремо закрити незалежний semantic review, історично придатний/схвалений baseline, нормативну applicability, G1, G4 і reference gate. Новий перехід у цьому PR не додавався.
