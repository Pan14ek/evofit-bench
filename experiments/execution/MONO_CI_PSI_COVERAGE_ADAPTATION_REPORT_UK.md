# Діагностичний звіт: покриття fitness та потреба в адаптації A0.3 → A0.4

> **Поточний статус:** source-bound DEVELOPMENT-запуск після виправлення binding SHA-256 evaluator configuration. Обидва evaluator capability inventories верифіковані у заявленому static scope, а п’ять graph-edge mappings і Reporting query-port mapping мають `COVERED`. Загальна адаптаційна діагностика лишається `NOT_EVALUABLE` через незалежні невирішені вимоги та нормативні обмеження. Це не формальне схвалення і не виміряний результат Method P.

## Поточний запуск та архів

- База PR: `main` `9cd4d3560c3cc32e38ecfccfd834a5f15a06055d`.
- Код запуску: `1d48249a98429058ae7bbf724250b518a843eafb`.
- Перехід: A0.3 `26a9bb667da7d0938e38aca15d2bf29fd1de4829` (`7b951421395f532ca403dab09d76902ff08a807d`) → A0.4 `d3101c0d3aa9b7b709253b6ec7518416f05f65b9` (`2b436e0aaf09403ea516d73d20a466a122f86592`).
- Виконання: `DEV_PSI_TRANSITION_GHA_40306427232_1`, режим `DEVELOPMENT_METHOD_EXECUTION_ONLY`; [успішний GitHub Actions run](https://github.com/Pan14ek/evofit-bench/actions/runs/40306427232).
- [Новий приватний prerelease з архівом](https://github.com/Pan14ek/evofit-bench/releases/tag/mono-ci-psi-transition-40306427232-1). ZIP SHA-256: `9557934af144f6c8bdb1e5007222c1e5a41396363a1862d9e7ffc04de52f5a54`. Завантажений sidecar збігся; `transition-verify` повернув `PASS`, 445 учасників. Actions artifact storage було заповнене, тому workflow використав prerelease fallback і не перезаписував попередній release.
- Ключові digest-и архіву: `development_run.json` — `972ffaa489a24dcd153ebf89938a524da4f13f1f685d0100df5235a771e1fae1`; `PSI/raw/method-result.json` — `77d2db46fde7f003a089a1b09417e04fe8de004c9e602af838cf859cbdcf55d2`; `diagnostics/adaptation-necessity-assessment.json` — `eef3bee1756dce0de062b249c1e0edb2e99e8089bb70ef29f4aed98fa7e463fc`.

## Виправлений integration defect

У `_evaluator_capabilities()` файл `experiments/execution/tooling/mono_ci_psi_transition.py` читав `run["evaluator_configuration_sha256"]`. `run_fresh_evaluator()` у `mono_ci_psi_evidence.py` записує ту саму ідентичність у поле `configuration_sha256`, тому попередня перевірка отримувала `None` і позначала допустимі capabilities як `UNVERIFIED`.

Верифікатор тепер читає саме `configuration_sha256` і приймає його лише як lowercase 64-символьний SHA-256, рівний незалежно обчисленому digest copied configuration artifact. Він також звіряє digest із `evidence.evaluator.configuration_digest`. Missing, malformed та mismatched digests fail closed. Інші перевірки — source revision, повнота inspection, execution/compliance, конфігураційна відповідність evaluator diagnostics і representation binding — збережено. Нового alias і ослаблення digest contract немає.

## Before/after діагностика

| Dimension | До виправлення — run `40282986322` | Після виправлення — run `40306427232` |
|---|---|---|
| Configuration digest binding | Consumer шукав `evaluator_configuration_sha256`, runner повертав `configuration_sha256` | Поле runner використано напряму; record, evaluator evidence і copied config digest збігаються |
| `AC_PUBLIC_API` capabilities | `INCOMPLETE_OR_UNVERIFIED`; усі capability statuses `UNVERIFIED` | До/після: `VERIFIED_FOR_DECLARED_STATIC_SCOPE`; обидві capabilities `VERIFIED_STATIC_SCOPE` |
| `AC_MODULE_GRAPH` capabilities | `INCOMPLETE_OR_UNVERIFIED`; усі capability statuses `UNVERIFIED` | До/після: `VERIFIED_FOR_DECLARED_STATIC_SCOPE`; обидві capabilities `VERIFIED_STATIC_SCOPE` |
| Requirement-capability comparison | Query port та всі п’ять edges — `UNRESOLVED` через неперевірені capabilities | Query port і всі п’ять edges — `COVERED` за типізованими mapping rules |
| Adaptation necessity | Обидва controls `NOT_EVALUABLE` | Обидва controls залишилися `NOT_EVALUABLE`, але без digest-binding reason codes |
| Method Ψ | `HOLD`; 0 операцій | `HOLD`; 0 операцій |

У всіх чотирьох реальних evaluator observation records configuration digests збігаються з відповідними implementation artifacts:

- `AC_PUBLIC_API`: `8853c3a933b23f698c7ba7c5b6e511f292e8d9285dc0de4378741c53e466f7bb`.
- `AC_MODULE_GRAPH`: `1abae6871a477ff2a07685ad645a70defa2f1ac6745598ae4cdc35aab4e95bf6`.

## Вимоги та mappings

Вимоги й надалі походять незалежно від evaluator configuration — із digest-bound A0.3/A0.4 state manifests. Governance requirements маніфестів лишаються вимогами до доказового процесу, а не fitness controls. Capability values походять з evaluator configuration та її реальних outputs. Технічне `COVERED` нижче підтверджує лише mapping у визначеному static scope; воно не підтверджує нормативну authority чи повну семантичну достатність.

| Control | A0.3 вимога → A0.4 вимога | Verified capability | A0.4 mapping |
|---|---|---|---|
| `AC_PUBLIC_API` | Тимчасовий exception `reporting_tasks_query_intermediate_v1` → `architecture.public_api.reporting_query_port` | `evaluator.public_api.reporting_query_port_boundary` і `evaluator.public_api.temporary_exception_scope` | `MAP-REPORTING-QUERY-PORT-TO-A1-PUBLIC-API-V1`: `COVERED` |
| `AC_MODULE_GRAPH` | П’ять дозволених edges; набір не змінився: `reporting→tasks`, `tasks→audit`, `tasks→notifications`, `tasks→users`, `users→audit` | `evaluator.module_graph.allowed_dependency_policy` і `evaluator.module_graph.acyclicity` | `MAP-MODULE-DEPENDENCY-TO-A1-ALLOWED-EDGE-V1`: кожен із п’яти mappings `COVERED` |

Requirement inventory повний лише для оголошених типів manifest (`COMPLETE_FOR_DECLARED_MANIFEST_TYPES`); повнота всього requirement universe лишається `UNKNOWN`. Невирішеними залишаються partial catalog obligations, manifest invariants поза вибраним evaluator scope та authority відповідної policy (`DRAFT`, registry `OPEN`, approval source відсутній). Ці причини залишилися в діагностиці після усунення digest defect.

## Результат adaptation-necessity assessment

Обидва controls повернули `assessment_status=NOT_EVALUABLE`, `configuration_change_necessity=NOT_EVALUABLE`, `pair_semantic_validity=UNKNOWN`.

- `AC_PUBLIC_API`: `INDEPENDENT_REQUIREMENTS_REMAIN_UNRESOLVED`, `NORMATIVE_APPLICABILITY_NOT_APPROVED`, `REQUIREMENT_UNIVERSE_COMPLETENESS_UNKNOWN`.
- `AC_MODULE_GRAPH`: ті самі три причини та `DYNAMIC_DEPENDENCY_EDGE_COMPLETENESS_UNKNOWN`.

Отже, digest defect було технічно усунуто: обидва verified capability inventories й усі задекларовані manifest-to-capability mappings тепер проходять перевірку. Цього недостатньо, щоб зробити `RETAIN_CANDIDATE` або `ADAPTATION_NEEDED` обґрунтованими за повного requirement universe та схваленої applicability. Результат не був заданий наперед.

## Method Ψ та дослідницькі межі

Method Ψ виконався без змін у `p_adaptation.py`, Method Ψ selection logic або method inputs. Фактичний governance result — `HOLD`; operation plan порожній (`0` операцій), prediction не видано, scoring і measurement — `NOT_EXECUTED`. Hold reasons: `COST_MODEL_UNRESOLVED`, `MANDATORY_APPLICABILITY_UNKNOWN`, `UNKNOWN_MANDATORY_LINK_PREVENTS_TRANSITION`. Raw result SHA-256: `77d2db46fde7f003a089a1b09417e04fe8de004c9e602af838cf859cbdcf55d2`.

Залишаються невирішеними повнота requirement universe, normative applicability та policy authority, semantic adequacy/independent review, історична ідентичність і схвалення baseline, а для module graph — completeness dynamic dependencies. Baseline лишається `PROSPECTIVE_RECONSTRUCTION_NOT_HISTORICAL`/`NOT_APPROVED`; policy — `DRAFT_OPEN_UNAPPROVED`; evidence trust scope — `TEST_ONLY`. Статуси `NO_GO`, `P_ALGORITHM_STATUS=NOT_READY`, `G1=INCOMPLETE`, `G4=NOT_AUTHORIZED` та `G-A1-C4-REF-FROZEN=NOT_READY` не змінювалися. Frozen scenarios, B0 configuration, policy definitions та попередні архіви не змінювалися.

Попередній run `40236384716` з V1-діагнозом `RETAIN_CANDIDATE` лишається незмінним історичним архівом; circular V1 результат не використовується як підстава для висновків у цій V2 діагностиці. Безпосередньо попередній run `40282986322` також лишається незміненим: його `UNVERIFIED` capability результат був наслідком integration mismatch, а не доказом відсутньої нормативної вимоги.

## Регресійні перевірки

- **A — коректний digest:** обидва evaluator inventories стають `VERIFIED_FOR_DECLARED_STATIC_SCOPE`, коли digest збігається і решта доказів валідна.
- **B/C — неправильний або відсутній digest:** capability statuses лишаються `UNVERIFIED`.
- **D — недостатні інші докази:** malformed digest, неправильний source commit, incomplete inspection, inconsistent diagnostics, mismatched evidence digest або відсутній representation binding не проходять тільки на підставі matching configuration SHA.
- **E — реальна execution regression:** A0.3 → A0.4 records із `run_fresh_evaluator()` читаються capability verifier без перейменування; integration перевіряє digests against copied configuration artifacts, capability statuses та `COVERED` mappings.

Перевірено detached checksum і локальний archive readback:

```text
shasum -a 256 mono-ci-psi-transition-40306427232-1.zip
9557934af144f6c8bdb1e5007222c1e5a41396363a1862d9e7ffc04de52f5a54

uv run --frozen --extra dev python -m experiments.execution.tooling.mono_ci_b0_psi_archive \
  transition-verify --archive mono-ci-psi-transition-40306427232-1.zip \
  --extract-to <readback-directory>
verification_status: PASS; member_count: 445
```

Наступна межа — незалежні докази нормативної authority та completeness, semantic review і достатності динамічної graph інспекції. Поточне технічне виправлення і цей звіт їх не встановлюють та не просувають жоден research gate.
