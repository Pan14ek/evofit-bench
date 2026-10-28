# Підсумок контрольованих умов C0, C1 і C2

## Статус C2 V2

C2 V2 було запущено один раз як авторську умову `TEST_ONLY`. GitHub Actions
[run 40669036608](https://github.com/Pan14ek/evofit-bench/actions/runs/40669036608)
завершився `FAILURE`. Підготовчі регресії, `make development-quality`,
Docker-isolation preflight і перевірка часткового доказового пакета пройшли.
Єдиний warmup завершився помилкою ізольованого процесу методу; три виміряні
повтори після цього не запускалися. Статус C2 — `PARTIAL`, а не `HOLD`,
`REJECT` чи `ACCEPT`.

До warmup було заморожено commit `6a800d49c213bc99e0bd912ab6310dda9665f9a9`.
Freeze SHA-256: `2cad854c56b878e8a3ed0fec849865093ce63581733da25d3649e9b3330ee5c7`;
protocol SHA-256: `9cf20f31692afc2fb0eb94dd3c4cbbdbb407e5cbd91810d5c1a8b83972696790`;
profile SHA-256: `3c1d41a74b6ef0ddbcfee1a41ad51a49fb204326a3d3a61d97034aa9cbfc0f6b`;
Docker preflight SHA-256:
`d125fbb2d585d0b3441857ac72aeea5f34750482fa72d6566fb21b534c94456b`.
Застосунок мав той самий Git tree до і після переходу:
`007196f68652bc13f6798805793ffdfae96f95f7`. Core-файли `p_adaptation.py` і
`p_applicability.py` залишилися байтово незмінними; застосовано лише окремі
версійовані C2 V2 adapters.

**Фактична причина зупинки:** traceback ізольованого процесу закінчився на
`adapt_candidate_v1 → validate_candidate → load_schema` повідомленням
`Unknown execution schema: candidate_configuration.schema.json`. Цієї схеми не
було у зібраному method-runtime schema allowlist. Це помилка пакування
виконуваного методу, а не рішення governance і не доказ недостатності чи
недійсності retain-входів. Метод-процес завершився з кодом `1` за `1887.992`
мс. У частковому записі `operation_plan`, governance decision і candidate
validation позначені `NOT_OBSERVED` / `NOT_EXECUTED`; їх не можна відновлювати
з traceback. Кандидат не був перевірений, прийнятий, застосований або
оцінений.

Після цього запуску виправлено лише пакування runtime: наявну legacy candidate
schema додано до allowlist, а focused regression тест тепер перевіряє її
присутність. Це post-run інженерне виправлення; воно не входить у freeze C2,
не змінює збережений результат і не супроводжувалося повторним запуском C2.

## Порівняння фактичних станів

| Умова | Спостережений план | Governance | Кандидат та застосування |
| --- | --- | --- | --- |
| **C0** — контрольний V2 | Порожній; `ADD` не було | `HOLD` у warmup і трьох виміряних запусках | Кандидат матеріалізовано, але не застосовано |
| **C1** — позитивний TEST_ONLY ADD | `ADD AC_DATA_OWNERSHIP` у кожному з трьох виміряних запусків | `HOLD: IMPACTED_RETAIN_REASSESSMENT_MISSING` | Кандидат валідовано й виконано на clean і ownership-negative джерелах; governance його не прийняв і конфігурацію не застосовано |
| **C2 V1** — попередній retain-вхід | Warmup мав порожній план | `HOLD` через невирішене global policy closure | Не було прийнятої конфігурації; три виміряні запуски не починалися |
| **C2 V2** — exact-set, версійований TEST_ONLY вхід | Не спостережений: method process завершився під час candidate validation | Не спостережене | Не матеріалізовано у підтвердженому method result; не прийнято, не застосовано й не оцінено |

У C1 дві наявні representations були `REP_RECON_B0_A04_PUBLIC_API_CI_V1`
(`AC_PUBLIC_API`) і `REP_RECON_B0_A04_MODULE_GRAPH_CI_V1`
(`AC_MODULE_GRAPH`). Їхні C1 source-bound pair records містили
`VALID_TEST_ONLY`, `COMPLIANT`, process exit `0` та повну інспекцію `31/31`;
config digests — `8853c3a933b23f698c7ba7c5b6e511f292e8d9285dc0de4378741c53e466f7bb`
і `1abae6871a477ff2a07685ad645a70defa2f1ac6745598ae4cdc35aab4e95bf6`;
спільний evaluator source manifest —
`5c17373ba8896ef0c443d826bd0064168ec7c5759c7973f9602b6c2c715b169c`.
Незмінне дерево застосунку було
`007196f68652bc13f6798805793ffdfae96f95f7`.

Отже, наявні артефакти дозволяли сформувати source-bound позитивні retain
оцінки **лише в окремо задекларованому точному TEST_ONLY наборі**. C2 V2
визначив рівно `AC_PUBLIC_API`, `AC_MODULE_GRAPH` і `AC_DATA_OWNERSHIP`, по
одному claim на обов’язок і стан; інші 15 catalog obligations лишалися
`UNKNOWN`. Це не є незалежним підтвердженням семантичної адекватності або
зовнішньою нормативною підставою. Через збій методу не можна стверджувати, що
Ψ фактично видав чи використав retain-рішення для C2.

## Evaluator-спостереження, час і вартість

У частково зібраному C2 warmup B0-контролі `AC_PUBLIC_API` та
`AC_MODULE_GRAPH` були `COMPLIANT` до і після переходу. Їхній process time до
переходу становив відповідно `155.014` і `156.077` мс; після — `186.875` і
`188.184` мс. Окремий clean `AC_DATA_OWNERSHIP` input diagnostic був
`COMPLIANT` за `113.946` мс. Це лише наявні observations до завершення Ψ:
ownership-negative evaluator для C2 не запускався, candidate evaluators не
виконувалися, а governance cost verdict відсутній. Ліміт лишався `225` мс на
один доданий evaluator виклик; повну двоумовну C2 вартість не виміряно.

Для C2 повний час переходу відсутній, три виміряні Ψ значення й стандартне
відхилення не визначені. `1887.992` мс — тривалість невдалого method subprocess,
а не успішне вимірювання Ψ. Для порівняння, у трьох C1 повтореннях Ψ було
`2683.555`, `2632.959` і `2620.134` мс (середнє `2645.549` мс, вибіркове
стандартне відхилення `33.533` мс). C1 ownership evaluator окремо займав
`162.788–164.008` мс на clean і `155.179–159.657` мс на negative input;
повний час переходу C1 також недоступний через hosted receipt failure.
Ці три повтори — одна архітектурна зміна, а не незалежна статистична вибірка.

| Сценарій | B0 | Кандидат |
| --- | --- | --- |
| C1 clean A0.5 | `AC_PUBLIC_API` і `AC_MODULE_GRAPH`: `COMPLIANT` | Усі три evaluator-и: `COMPLIANT` |
| C1 ownership-negative | Обидва B0 evaluator-и `COMPLIANT`; ownership-порушення не виявлено | `AC_DATA_OWNERSHIP`: `NON_COMPLIANT`, `FOREIGN_TABLE_ACCESS`; два B0 evaluator-и лишилися `COMPLIANT` |
| C2 V2 | У partial warmup `AC_PUBLIC_API` і `AC_MODULE_GRAPH` були `COMPLIANT`; окремий clean ownership diagnostic теж `COMPLIANT` | Немає candidate result, негативного запуску або порівняння |

## Докази та межі висновку

GitHub Actions artifact `mono-ci-a05-positive-add-c2-40669036608-1` (artifact
ID `12807372736`) має GitHub digest
`sha256:57fbeca8e65ef49c698d3d732a06982d627a106aad957652adb1e18638da3f40`.
Збережені `C2_RESULTS.json` SHA-256
`81370ad3b219115ef171400ae32c1fa4dca8e56ea8153512818e271501c7fe4a`, pre-run
freeze SHA-256 `2cad854c56b878e8a3ed0fec849865093ce63581733da25d3649e9b3330ee5c7`
та partial execution SHA-256
`1a5400b1707febd38ecadd33fb7a07b61c41fbc75dcc9658d56e08d357139a0f`.
Локальний `c2 verify --version 2` підтвердив
`verification_status=PASS`, `archive_count=0`; усі entries у
`SHA256SUMS` звірилися. Повного C2 transition archive немає, тому окремий
post-run recovery release не створювався.

C1 raw transitions залишаються без змін. Їхній окремий
[post-run recovery release](https://github.com/Pan14ek/evofit-bench/releases/tag/mono-ci-a05-positive-add-recovery-40612830900-1)
має перевірений SHA-256
`3c3aaaa0ab675ec33158cebba9eae565bacab973a09e98ba5e48273952c760a2`.
Початковий C1 hosted run лишається `FAILURE`, а недоступний повний час
переходу не відновлено.

**Висновок для монографії:** C0 зафіксував фактичний `HOLD` без `ADD`; C1
зафіксував фактичний obligation-level `ADD` із фінальним `HOLD`, а
матеріалізований кандидат був лише випробуваний і не застосований; C2 V2 не
дав спостереженого operation plan чи governance decision через помилку
пакування схеми в ізольований runtime. Тому варіант **B**: `ACCEPT` не
досягнуто, і C1 залишається останнім завершеним монографічним експериментом.
Усі результати — авторські `TEST_ONLY`; вони не доводять незалежну
семантичну адекватність, узагальнену ефективність чи статистичну перевагу.
`P_ALGORITHM_STATUS=NOT_READY`, `G1=INCOMPLETE`, `G4=NOT_AUTHORIZED`,
reference `NOT_READY`, scoring `NOT_EXECUTED`.
