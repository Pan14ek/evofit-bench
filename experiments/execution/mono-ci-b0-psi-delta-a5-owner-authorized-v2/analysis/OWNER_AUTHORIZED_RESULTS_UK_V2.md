# Власницьки авторизоване DEVELOPMENT-дослідження ΔA5 — V2


## Пост-run корекція похідного аналізу

Цей звіт є post-run корекцією для run `40579333932`; вимірювання та raw archives не змінювалися. Первісний freeze прив'язував код аналізу до SHA-256 `cdb8c1eeb880935311a109586a32dd0583e32db288373fe563c6b9378b72a331`; код цієї корекції має SHA-256 `18bf57666877b887917e4d3ba542818b4a374e85018e2365cf1d14bbd7f411f8`. У V3 `analysis-summary.json` окремо подає 60 калібрувальних B0 evaluator-процесів і 12 B0 evaluator-процесів у виміряних transition runs; попереднє неоднозначне агреговане поле замінене цими двома ключами. Порівняльна таблиця повноти тепер окремо рахує measured sample rows і warmups з архівів: V1 — 30 успішних, 30 failed виміряних samples і 6 warmups; V2 — 60 успішних, 0 failed виміряних samples і 6 warmups. Це відділяє warmup outcomes, які входили до попередніх aggregate execution counts, від виміряних повторів. Первинна release залишається byte-preserved; її readback і freeze verification пройшли до цієї корекції.

## Класифікація і межі

Study ID: `MONO_CI_B0_PSI_DELTA_A5_OWNER_AUTHORIZED_DEV_V2`. Класифікація — `RESEARCH_OWNER_AUTHORIZED_EXPLORATORY_DEVELOPMENT`; workflow run: `40579333932`. Це одна архітектурна одиниця A0.4→A0.5 і чотири технічні спроби (один прогрів і три вимірювані повтори). Результати не є незалежним порівнянням, не завершують G1/G4 і не встановлюють наукову перевагу. P algorithm лишається NOT_READY, G1 INCOMPLETE, G4 NOT_AUTHORIZED, scoring NOT_EXECUTED, coverage UNKNOWN.

## Порівняння повноти V1 та V2

| Набір | Calls planned | Measured successful | Measured failed | Warmups | Measured not run | Transitions: completed / failed | Статус B0/Ψ |
|---|---:|---:|---:|---:|---:|---:|---|
| V1 (`MONO_CI_B0_PSI_DELTA_A5_OWNER_AUTHORIZED_DEV_V1`; run 40499692594) | 66 | 30 | 30 | 6 | 0 | 0 / 4 | порівняння NOT_EXECUTED; Ψ NOT_OBSERVED |
| V2 (`MONO_CI_B0_PSI_DELTA_A5_OWNER_AUTHORIZED_DEV_V2`; run 40579333932) | 66 | 60 | 0 | 6 | 0 | 4 / 0 | див. окремі фактичні рядки нижче |

| Умова | Оцінювач | V1 n | V1 failed | V1 mean ms | V2 n | V2 failed | V2 mean ms |
|---|---|---:|---:|---:|---:|---:|---:|
| A0_5_CLEAN | AC_PUBLIC_API | 10 | 0 | 160.162 | 10 | 0 | 166.039 |
| A0_5_CLEAN | AC_MODULE_GRAPH | 10 | 0 | 168.403 | 10 | 0 | 171.464 |
| A0_5_CLEAN | AC_DATA_OWNERSHIP | 10 | 0 | 166.436 | 10 | 0 | 172.726 |
| EXISTING_NEGATIVE_PROBE | AC_PUBLIC_API | 0 | 10 | None | 10 | 0 | 164.716 |
| EXISTING_NEGATIVE_PROBE | AC_MODULE_GRAPH | 0 | 10 | None | 10 | 0 | 171.5 |
| EXISTING_NEGATIVE_PROBE | AC_DATA_OWNERSHIP | 0 | 10 | None | 10 | 0 | 173.907 |

Вибірки калібрування V1 та V2 збережені окремо. Протокол V2 вибрав умови `A0_5_CLEAN, EXISTING_NEGATIVE_PROBE` за замороженим правилом порівнянності середовища; часові вибірки не об'єднувалися.

## Калібрування: виміряні результати

За даними `MONO_CI_B0_PSI_DELTA_A5_OWNER_AUTHORIZED_DEV_V1`, run 40499692594, сирого `calibration.zip` SHA-256 `d4851c292497728b98af5a75aa8f01883541eb5672274896cf6065cd0c612d27` та первинної обробки функцією `_summarize_calibration` (десять виміряних повторів; прогрів вилучено; p90 — nearest-rank), середні CLI-часи трьох оцінювачів на чистому A0.5 становили 160.162–168.403 мс. У межах цих clean-source вибірок повну source inspection із нульовими missing, altered і unexpected файлами зафіксовано у 30/30 виміряних запусків.

| Умова | Оцінювач | n | Failed | Mean ms | Median ms | SD ms | Min–max ms | p90 ms |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| A0_5_CLEAN | AC_DATA_OWNERSHIP | 10 | 0 | 172.726 | 172.6 | 2.779 | 168.746–176.674 | 175.501 |
| A0_5_CLEAN | AC_MODULE_GRAPH | 10 | 0 | 171.464 | 171.139 | 1.469 | 169.503–174.04 | 173.478 |
| A0_5_CLEAN | AC_PUBLIC_API | 10 | 0 | 166.039 | 166.754 | 1.879 | 162.748–168.492 | 167.924 |
| EXISTING_NEGATIVE_PROBE | AC_DATA_OWNERSHIP | 10 | 0 | 173.907 | 173.634 | 1.923 | 170.837–177.215 | 176.212 |
| EXISTING_NEGATIVE_PROBE | AC_MODULE_GRAPH | 10 | 0 | 171.5 | 171.583 | 2.585 | 166.998–175.052 | 173.914 |
| EXISTING_NEGATIVE_PROBE | AC_PUBLIC_API | 10 | 0 | 164.716 | 164.279 | 1.352 | 162.914–167.262 | 165.974 |

V2 числові рядки відтворюються зі study `MONO_CI_B0_PSI_DELTA_A5_OWNER_AUTHORIZED_DEV_V2`, workflow run `40579333932`, `calibration.zip` SHA-256 `211cd9bef19c0ad377cc3a01f183b7e062596da9f1a548fe1d71159e502dd837` та `evaluator-samples.csv`; обробка: `descriptive_statistics`/`_summarize_calibration`, прогрів не входить до часу. На одне architecture-level спостереження статистичну значущість не обчислено.

## Перехід: фактичні B0 та Method Ψ

| Execution ID | Роль | B0 status | B0 outcomes (exit/scope) | Ψ process | Ψ decision | Operations | Ψ reasons | Candidate state/status/digest | Candidate outcomes/parity | Candidate cost ms | Estimated added CI ms/build | Transition ms | Ψ ms | Error | Evidence SHA-256 |
|---|---|---|---|---|---|---|---|---|---|---:|---:|---:|---:|---|---|
| DEV_PSI_TRANSITION_OADEV_V2_DELTA_A5_20261027_WARMUP_00 | WARMUP | ALL_OUTPUTS_PARSED | A0_4_REPORT_QUERY_PORT:AC_PUBLIC_API=COMPLIANT (exit=0, scope=COMPLETE); A0_4_REPORT_QUERY_PORT:AC_MODULE_GRAPH=COMPLIANT (exit=0, scope=COMPLETE); A0_5_MODULE_DATA_OWNERSHIP:AC_PUBLIC_API=COMPLIANT (exit=0, scope=COMPLETE); A0_5_MODULE_DATA_OWNERSHIP:AC_MODULE_GRAPH=COMPLIANT (exit=0, scope=COMPLETE) | COMPLETED | HOLD | [] | {"governance":["APPLICABILITY_UNKNOWN","COST_MODEL_UNRESOLVED","COST_VERDICT_UNRESOLVED","INPUT_AUTHORITY_OR_COMPLETENESS_UNRESOLVED","INVARIANT_VERDICTS_NOT_ALL_POSITIVE","MANDATORY_APPLICABILITY_UNKNOWN","MANDATORY_CLASSIFICATION_UNRESOLVED","UNKNOWN_MANDATORY_LINK_PREVENTS_TRANSITION","VERIFIED_GOVERNANCE_PIPELINE_PROOF_MISSING"],"operation_hold":["COST_MODEL_UNRESOLVED","MANDATORY_APPLICABILITY_UNKNOWN","UNKNOWN_MANDATORY_LINK_PREVENTS_TRANSITION"]} | MATERIALIZED_UNAPPLIED / PASS / c91f52aba5301fc517639e089a0c7c39c82bea4d644d06091463d81b9287e81b | [{"candidate_negative":{"compliance":"COMPLIANT","evaluator_id":"AC_MODULE_GRAPH","execution_status":"COMPLETED","finding_codes":[]},"candidate_positive":{"compliance":"COMPLIANT","evaluator_id":"AC_MODULE_GRAPH","execution_status":"COMPLETED","finding_codes":[]},"negative_outcome_parity":true,"positive_outcome_parity":true,"representation_id":"REP_RECON_B0_A04_MODULE_GRAPH_CI_V1"},{"candidate_negative":{"compliance":"COMPLIANT","evaluator_id":"AC_PUBLIC_API","execution_status":"COMPLETED","finding_codes":[]},"candidate_positive":{"compliance":"COMPLIANT","evaluator_id":"AC_PUBLIC_API","execution_status":"COMPLETED","finding_codes":[]},"negative_outcome_parity":true,"positive_outcome_parity":true,"representation_id":"REP_RECON_B0_A04_PUBLIC_API_CI_V1"}] | 652.908 | 0 | 12670.667 | 1950.591 | ["COST_MODEL_UNRESOLVED","MANDATORY_APPLICABILITY_UNKNOWN","UNKNOWN_MANDATORY_LINK_PREVENTS_TRANSITION"] | 2566fc6542829d05d42ae84132a2eb3c855347eeef91178e05f3312ea3bcc5f8 |
| DEV_PSI_TRANSITION_OADEV_V2_DELTA_A5_20261027_MEASURED_01 | MEASURED | ALL_OUTPUTS_PARSED | A0_4_REPORT_QUERY_PORT:AC_PUBLIC_API=COMPLIANT (exit=0, scope=COMPLETE); A0_4_REPORT_QUERY_PORT:AC_MODULE_GRAPH=COMPLIANT (exit=0, scope=COMPLETE); A0_5_MODULE_DATA_OWNERSHIP:AC_PUBLIC_API=COMPLIANT (exit=0, scope=COMPLETE); A0_5_MODULE_DATA_OWNERSHIP:AC_MODULE_GRAPH=COMPLIANT (exit=0, scope=COMPLETE) | COMPLETED | HOLD | [] | {"governance":["APPLICABILITY_UNKNOWN","COST_MODEL_UNRESOLVED","COST_VERDICT_UNRESOLVED","INPUT_AUTHORITY_OR_COMPLETENESS_UNRESOLVED","INVARIANT_VERDICTS_NOT_ALL_POSITIVE","MANDATORY_APPLICABILITY_UNKNOWN","MANDATORY_CLASSIFICATION_UNRESOLVED","UNKNOWN_MANDATORY_LINK_PREVENTS_TRANSITION","VERIFIED_GOVERNANCE_PIPELINE_PROOF_MISSING"],"operation_hold":["COST_MODEL_UNRESOLVED","MANDATORY_APPLICABILITY_UNKNOWN","UNKNOWN_MANDATORY_LINK_PREVENTS_TRANSITION"]} | MATERIALIZED_UNAPPLIED / PASS / c91f52aba5301fc517639e089a0c7c39c82bea4d644d06091463d81b9287e81b | [{"candidate_negative":{"compliance":"COMPLIANT","evaluator_id":"AC_MODULE_GRAPH","execution_status":"COMPLETED","finding_codes":[]},"candidate_positive":{"compliance":"COMPLIANT","evaluator_id":"AC_MODULE_GRAPH","execution_status":"COMPLETED","finding_codes":[]},"negative_outcome_parity":true,"positive_outcome_parity":true,"representation_id":"REP_RECON_B0_A04_MODULE_GRAPH_CI_V1"},{"candidate_negative":{"compliance":"COMPLIANT","evaluator_id":"AC_PUBLIC_API","execution_status":"COMPLETED","finding_codes":[]},"candidate_positive":{"compliance":"COMPLIANT","evaluator_id":"AC_PUBLIC_API","execution_status":"COMPLETED","finding_codes":[]},"negative_outcome_parity":true,"positive_outcome_parity":true,"representation_id":"REP_RECON_B0_A04_PUBLIC_API_CI_V1"}] | 656.558 | 0 | 13015.458 | 1891.537 | ["COST_MODEL_UNRESOLVED","MANDATORY_APPLICABILITY_UNKNOWN","UNKNOWN_MANDATORY_LINK_PREVENTS_TRANSITION"] | 76024640bf1a5bfc8771f91a7c9c113c7486f44e28f6290b56dafb32867ae890 |
| DEV_PSI_TRANSITION_OADEV_V2_DELTA_A5_20261027_MEASURED_02 | MEASURED | ALL_OUTPUTS_PARSED | A0_4_REPORT_QUERY_PORT:AC_PUBLIC_API=COMPLIANT (exit=0, scope=COMPLETE); A0_4_REPORT_QUERY_PORT:AC_MODULE_GRAPH=COMPLIANT (exit=0, scope=COMPLETE); A0_5_MODULE_DATA_OWNERSHIP:AC_PUBLIC_API=COMPLIANT (exit=0, scope=COMPLETE); A0_5_MODULE_DATA_OWNERSHIP:AC_MODULE_GRAPH=COMPLIANT (exit=0, scope=COMPLETE) | COMPLETED | HOLD | [] | {"governance":["APPLICABILITY_UNKNOWN","COST_MODEL_UNRESOLVED","COST_VERDICT_UNRESOLVED","INPUT_AUTHORITY_OR_COMPLETENESS_UNRESOLVED","INVARIANT_VERDICTS_NOT_ALL_POSITIVE","MANDATORY_APPLICABILITY_UNKNOWN","MANDATORY_CLASSIFICATION_UNRESOLVED","UNKNOWN_MANDATORY_LINK_PREVENTS_TRANSITION","VERIFIED_GOVERNANCE_PIPELINE_PROOF_MISSING"],"operation_hold":["COST_MODEL_UNRESOLVED","MANDATORY_APPLICABILITY_UNKNOWN","UNKNOWN_MANDATORY_LINK_PREVENTS_TRANSITION"]} | MATERIALIZED_UNAPPLIED / PASS / c91f52aba5301fc517639e089a0c7c39c82bea4d644d06091463d81b9287e81b | [{"candidate_negative":{"compliance":"COMPLIANT","evaluator_id":"AC_MODULE_GRAPH","execution_status":"COMPLETED","finding_codes":[]},"candidate_positive":{"compliance":"COMPLIANT","evaluator_id":"AC_MODULE_GRAPH","execution_status":"COMPLETED","finding_codes":[]},"negative_outcome_parity":true,"positive_outcome_parity":true,"representation_id":"REP_RECON_B0_A04_MODULE_GRAPH_CI_V1"},{"candidate_negative":{"compliance":"COMPLIANT","evaluator_id":"AC_PUBLIC_API","execution_status":"COMPLETED","finding_codes":[]},"candidate_positive":{"compliance":"COMPLIANT","evaluator_id":"AC_PUBLIC_API","execution_status":"COMPLETED","finding_codes":[]},"negative_outcome_parity":true,"positive_outcome_parity":true,"representation_id":"REP_RECON_B0_A04_PUBLIC_API_CI_V1"}] | 669.194 | 0 | 13053.834 | 1929.674 | ["COST_MODEL_UNRESOLVED","MANDATORY_APPLICABILITY_UNKNOWN","UNKNOWN_MANDATORY_LINK_PREVENTS_TRANSITION"] | 0b21562a3424726b38047b19145cba6620b3109028ab37991d0ded534e8087d5 |
| DEV_PSI_TRANSITION_OADEV_V2_DELTA_A5_20261027_MEASURED_03 | MEASURED | ALL_OUTPUTS_PARSED | A0_4_REPORT_QUERY_PORT:AC_PUBLIC_API=COMPLIANT (exit=0, scope=COMPLETE); A0_4_REPORT_QUERY_PORT:AC_MODULE_GRAPH=COMPLIANT (exit=0, scope=COMPLETE); A0_5_MODULE_DATA_OWNERSHIP:AC_PUBLIC_API=COMPLIANT (exit=0, scope=COMPLETE); A0_5_MODULE_DATA_OWNERSHIP:AC_MODULE_GRAPH=COMPLIANT (exit=0, scope=COMPLETE) | COMPLETED | HOLD | [] | {"governance":["APPLICABILITY_UNKNOWN","COST_MODEL_UNRESOLVED","COST_VERDICT_UNRESOLVED","INPUT_AUTHORITY_OR_COMPLETENESS_UNRESOLVED","INVARIANT_VERDICTS_NOT_ALL_POSITIVE","MANDATORY_APPLICABILITY_UNKNOWN","MANDATORY_CLASSIFICATION_UNRESOLVED","UNKNOWN_MANDATORY_LINK_PREVENTS_TRANSITION","VERIFIED_GOVERNANCE_PIPELINE_PROOF_MISSING"],"operation_hold":["COST_MODEL_UNRESOLVED","MANDATORY_APPLICABILITY_UNKNOWN","UNKNOWN_MANDATORY_LINK_PREVENTS_TRANSITION"]} | MATERIALIZED_UNAPPLIED / PASS / c91f52aba5301fc517639e089a0c7c39c82bea4d644d06091463d81b9287e81b | [{"candidate_negative":{"compliance":"COMPLIANT","evaluator_id":"AC_MODULE_GRAPH","execution_status":"COMPLETED","finding_codes":[]},"candidate_positive":{"compliance":"COMPLIANT","evaluator_id":"AC_MODULE_GRAPH","execution_status":"COMPLETED","finding_codes":[]},"negative_outcome_parity":true,"positive_outcome_parity":true,"representation_id":"REP_RECON_B0_A04_MODULE_GRAPH_CI_V1"},{"candidate_negative":{"compliance":"COMPLIANT","evaluator_id":"AC_PUBLIC_API","execution_status":"COMPLETED","finding_codes":[]},"candidate_positive":{"compliance":"COMPLIANT","evaluator_id":"AC_PUBLIC_API","execution_status":"COMPLETED","finding_codes":[]},"negative_outcome_parity":true,"positive_outcome_parity":true,"representation_id":"REP_RECON_B0_A04_PUBLIC_API_CI_V1"}] | 658.133 | 0 | 12977.58 | 1909.712 | ["COST_MODEL_UNRESOLVED","MANDATORY_APPLICABILITY_UNKNOWN","UNKNOWN_MANDATORY_LINK_PREVENTS_TRANSITION"] | 7a6e6391a441f44c4a63abb2d245120f59fe58a2f950edb5de0731497046da6c |

Повні дані кожної спроби, включно з candidate evaluator checks, додатковою вартістю перевірки кандидата, помилками, B0 raw streams і фазами, наведені в `transition-run-table.csv` та `analysis-summary.json`. Повні архіви перевірено чинним V4 verifier-ом; невдалі спроби перевірено окремою схемою PARTIAL_EXECUTION_EVIDENCE. Кожний рядок прив'язаний до digest окремого архіву або raw partial inventory.

### Часові та обчислювальні витрати трьох виміряних технічних повторів

| Показник | n | Missing | Mean ms | Median ms | Sample SD ms | Min–max ms | p90 ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| B0 evaluator process time (all states/evaluators) | 12 | 0 | 237.785 | 238.261 | 16.364 | 216.154–257.938 | 253.993 |
| Method Ψ subprocess | 3 | 0 | 1910.308 | 1909.712 | 19.075 | 1891.537–1929.674 | 1929.674 |
| Candidate evaluator validation | 3 | 0 | 661.295 | 658.133 | 6.886 | 656.558–669.194 | 669.194 |
| Full transition orchestration | 3 | 0 | 13015.624 | 13015.458 | 38.127 | 12977.58–13053.834 | 13053.834 |

Ці повтори належать одній парі архітектурних станів; це описові технічні виміри. Вартість candidate validation — фактично виміряна перевірка кандидатних evaluators. Estimated added CI ms/build із рядків кандидата є окремою оцінкою, а не виміром повного CI.

## Технічні помилки і пропущені дані

V1 зафіксував чотири bubblewrap-помилки `Failed RTM_NEWADDR: Operation not permitted`; результат Ψ, план операцій і кандидат не спостерігалися. Часткові B0 каталоги не були збережені. У V1 тієї самої історичної проби було збережено 33 raw-виходи; post-run технічний readback пройшов для 33 із них. Архів містить 30 failed виміряних sample records і три failed warmup records для негативної умови; початкові статуси та process durations не переписувалися. Readback SHA-256 `26f81d389a0af61ccaa15e34b803dbe380320e5b0a2ae6bab278fd0a964be2a0` підтверджує лише повторне source/scope зіставлення, а не новий запуск.

Попередня технічна спроба V2 (run `40569757224`) зупинилася до калібрування через невідповідність ідентичності baseline у коді технічного preflight. Це окремий pre-measurement failure, а не одна з чотирьох transition-спроб і не результат B0/Ψ. Її raw hosted preflight ZIP має readback `PASS`; SHA-256 наведено нижче.

| Workflow run | Stage | Calibration calls | Transitions | Ψ status | Error | Raw preflight ZIP SHA-256 |
|---:|---|---:|---:|---|---|---|
| 40569757224 | OWNER_AUTHORIZED_V2_TECHNICAL_PREFLIGHT | 0 | 0 | NOT_OBSERVED | OWNER_AUTHORIZED_V2_BASELINE_IDENTITY_MISMATCH | dbd0b4724aae79db3c9d0b0d472470b31f00287edbae3b11068795b1bc3df65f |

Окремо збережено перший post-measurement V2 запуск (run `40574090499`) та його заморожені partial archives. Усі чотири wrapper rows лишилися `FAILED` через `KeyError: 'evaluator_observations'`, але raw release readback показав завершений B0 та фактичний Ψ `HOLD` у кожній спробі, валідований, materialized-but-unapplied кандидат і parity із реконструйованим B0 на двох наявних candidate controls. Цей запуск не переписано; наступний freeze/run є окремою версіонованою спробою. Попередній release ZIP підтверджено локально за GitHub asset digest (`11f4ec5aa1a399c2b4314c9785e256d9c894b61923c5748796d77ac1f0cf3e64`), однак його `.sha256` посилався на абсолютний шлях runner temp і не давав portable `sha256sum --check` після завантаження. Новий workflow виправляє sidecar і перевіряє саме downloaded bytes.

| Попередній workflow run | Execution ID | Wrapper status | Raw Ψ process | Actual decision | Candidate validation | Wrapper error | Partial archive SHA-256 |
|---:|---|---|---|---|---|---|---|
| 40574090499 | DEV_PSI_TRANSITION_OADEV_V2_DELTA_A5_20261027_WARMUP_00 | FAILED | DEVELOPMENT_METHOD_EXECUTED | HOLD | valid | KeyError: 'evaluator_observations' | 3d5c58492ad600e0d13b815b249688307ec14f94c0b3c8dcd08a72fbb109ccf9 |
| 40574090499 | DEV_PSI_TRANSITION_OADEV_V2_DELTA_A5_20261027_MEASURED_01 | FAILED | DEVELOPMENT_METHOD_EXECUTED | HOLD | valid | KeyError: 'evaluator_observations' | 42e26b1058bf08c864dc77a0c53d888f9870cb72fbe9a78b2aeee68a9d070e5a |
| 40574090499 | DEV_PSI_TRANSITION_OADEV_V2_DELTA_A5_20261027_MEASURED_02 | FAILED | DEVELOPMENT_METHOD_EXECUTED | HOLD | valid | KeyError: 'evaluator_observations' | 4668554153df711e63e28f56e0c61e789f8fc1fe432e1d52dfe91033ea27acfd |
| 40574090499 | DEV_PSI_TRANSITION_OADEV_V2_DELTA_A5_20261027_MEASURED_03 | FAILED | DEVELOPMENT_METHOD_EXECUTED | HOLD | valid | KeyError: 'evaluator_observations' | f66dcbee1da4c1bccb01be051e0c5b43545481220b372d93b0f38098ed872de4 |

У V2 невиміряні, не запущені, помилкові та частково збережені фази збережено окремо у `technical-failures.csv`; інфраструктурна помилка не інтерпретується як HOLD. Якщо Method Ψ не видав валідний result, статус — NOT_OBSERVED. Якщо фактичне рішення було HOLD, його reason codes і raw digest збережені без змін.

| Спроба цього freeze | Run status | Помилка / причина | Evidence class | Evidence SHA-256 |
|---|---|---|---|---|
| — | — | — | — | — |

## Обмеження інтерпретації

Чотири переходи є технічними повторами однієї пари станів, а не незалежними архітектурними одиницями. Три статичні evaluators і відома історична probe не дають оцінки загальної чутливості/специфічності або незалежного holdout. Перевірена source inspection не доводить семантичної адекватності, нормативної applicability, повноти obligation denominator, representation coverage чи runtime architectural quality. Навіть валідований кандидат не є застосованою або незалежно схваленою конфігурацією.

## Запропонований висновок

У цьому owner-authorized exploratory DEVELOPMENT запуску B0 зберіг розібрані виходи у 4/4 переходах; Method Ψ завершився з exit code 0 у 4/4 спробах і повернув HOLD: 4. Фактичні блокувальні reason codes: APPLICABILITY_UNKNOWN, COST_MODEL_UNRESOLVED, COST_VERDICT_UNRESOLVED, INPUT_AUTHORITY_OR_COMPLETENESS_UNRESOLVED, INVARIANT_VERDICTS_NOT_ALL_POSITIVE, MANDATORY_APPLICABILITY_UNKNOWN, MANDATORY_CLASSIFICATION_UNRESOLVED, UNKNOWN_MANDATORY_LINK_PREVENTS_TRANSITION, VERIFIED_GOVERNANCE_PIPELINE_PROOF_MISSING. Method Ψ фактично сформував кандидат і запустив його валідацію, але рішення HOLD залишило конфігурацію MATERIALIZED_UNAPPLIED; застосованої адаптації не було. У наявних candidate controls parity з реконструйованим B0 становила 8/8; у межах цих перевірок поліпшення detection capability не зафіксовано. Одна пара станів A0.4→A0.5 і три технічні повтори не встановлюють загальної ефективності методу, verified mandatory coverage, runtime architectural quality, статистичної переваги або G1/G4; coverage залишається UNKNOWN, G1 INCOMPLETE, G4 NOT_AUTHORIZED, scoring NOT_EXECUTED.

## Трасування доказів

- V1: study `MONO_CI_B0_PSI_DELTA_A5_OWNER_AUTHORIZED_DEV_V1`, run `40499692594`, release [evidence release](https://github.com/Pan14ek/evofit-bench/releases/tag/mono-ci-psi-a05-owner-authorized-40499692594-1), calibration archive SHA-256 `d4851c292497728b98af5a75aa8f01883541eb5672274896cf6065cd0c612d27`, analysis inputs `historical-v1/calibration.zip` і `POST_RUN_PROBE_READBACK.json`.
- Попередня спроба V2: run `40574090499`, release [перша V2 evidence release](https://github.com/Pan14ek/evofit-bench/releases/tag/mono-ci-psi-a05-owner-authorized-v2-40574090499-1), outer archive SHA-256 `11f4ec5aa1a399c2b4314c9785e256d9c894b61923c5748796d77ac1f0cf3e64`, frozen `study-execution.json` SHA-256 `3c7fec4f589c7f4906ac9c7d044c65ed81a809d59347f5fb694a6c982d80fc32`, readback-record SHA-256 `81bc3ccd67c372554d51d36e9d28bf3222bd73837e9ed64067e00208f3c3c8c2`. Оригінальні wrapper failures і raw HOLD/candidate observations лишаються відокремленими від нового запуску.
- V2: study `MONO_CI_B0_PSI_DELTA_A5_OWNER_AUTHORIZED_DEV_V2`, frozen commit `b34165dc2e8a857be84a12d42d1545453e626fd7`, workflow run `40579333932`, calibration archive SHA-256 `211cd9bef19c0ad377cc3a01f183b7e062596da9f1a548fe1d71159e502dd837`; перехідні архіви й partial-evidence digests наведені у `transition-run-table.csv`.
- Обробка: `experiments.execution.tooling.mono_ci_psi_owner_authorized_v2` і `analysis-summary.json`; descriptive mean/median/sample SD/min/max/nearest-rank p90; без об'єднання V1/V2, без inferential significance і без coverage percentage.
