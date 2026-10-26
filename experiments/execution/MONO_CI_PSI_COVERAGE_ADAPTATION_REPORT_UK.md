# Діагностичний звіт: покриття fitness та потреба в адаптації A0.3 → A0.4

> **Статус:** свіжий source-bound DEVELOPMENT-запуск після виправлення незалежності вимог і evaluator capabilities. Діагноз `NOT_EVALUABLE` є технічним висновком про недостатність доказів; він не є схваленням або виміряним результатом Method P.

## Ідентичність запуску та архів

- База PR: `main` `9cd4d3560c3cc32e38ecfccfd834a5f15a06055d`.
- Код виправлення та source revision запуску: `8cf4ebc983c9b434e087c853bd317d96ff3645bf`.
- Перехід: A0.3 `26a9bb667da7d0938e38aca15d2bf29fd1de4829` (`7b951421395f532ca403dab09d76902ff08a807d`) → A0.4 `d3101c0d3aa9b7b709253b6ec7518416f05f65b9` (`2b436e0aaf09403ea516d73d20a466a122f86592`).
- Виконання: `DEV_PSI_TRANSITION_GHA_40282986322_1`, режим `DEVELOPMENT_METHOD_EXECUTION_ONLY`; [успішний GitHub Actions run](https://github.com/Pan14ek/evofit-bench/actions/runs/40282986322).
- [Новий приватний prerelease з архівом](https://github.com/Pan14ek/evofit-bench/releases/tag/mono-ci-psi-transition-40282986322-1). ZIP SHA-256: `d79f53a11a9d60f71c791de74248a55d04fe8dce28df3497af4e9cfd8d8d1cb1`; release sidecar збігся. Завантажений архів пройшов `transition-verify` (`PASS`, 445 учасників). Actions artifact storage було заповнене, тож workflow зберіг архів у новому приватному prerelease, не перезаписуючи попередній.
- Ключові внутрішні digest-и: `development_run.json` — `c6af8a0c6a85664bcd3ec5ef940fa2c7dd4fffbffb975d0bff90b48edc5be8b6`; `PSI/raw/method-result.json` — `4eb185a168584f5f7f85b4362f32dd61e12ada87a87e4de491a6684ac391169c`; `diagnostics/adaptation-necessity-assessment.json` — `c5e850c9c548b9e1b97d6add07b2436dd1fc10994daa56326e547fd1245070d3`.

Попередній запуск `40236384716` і його V1-діагноз `RETAIN_CANDIDATE` залишаються незміненими історичними доказами. Через спільне походження required і represented controls той V1 висновок не використовується для обґрунтування поточного висновку. Новий запуск створено з виправленим кодом і V2-діагностикою; попередній архів не переписувався.

## Незалежні вимоги та evaluator capabilities

Вимоги отримані з versioned architecture state manifests. Governance requirements з маніфестів збережені окремо як вимоги до доказового процесу, а не fitness controls. Evaluator capabilities отримані окремо з evaluator configuration та фактичних evaluator outputs. Збіг назв сам по собі не доводить семантичного покриття: застосовано окремі типізовані mapping rules і перевірку структурованих значень.

| Control | Маніфестні вимоги до переходу | Вимоги після переходу | Capability IDs до/після | Результат зіставлення після переходу |
|---|---|---|---|---|
| `AC_PUBLIC_API` | `architecture.public_api.temporary_exception:reporting_tasks_query_intermediate_v1` | `architecture.public_api.reporting_query_port` | `evaluator.public_api.reporting_query_port_boundary`; `evaluator.public_api.temporary_exception_scope` | Mapping `MAP-REPORTING-QUERY-PORT-TO-A1-PUBLIC-API-V1`; `UNRESOLVED` — capability не верифіковано |
| `AC_MODULE_GRAPH` | П’ять `architecture.module_graph.allowed_dependency` controls: `reporting→tasks`, `tasks→audit`, `tasks→notifications`, `tasks→users`, `users→audit` | Ті самі п’ять дозволених напрямків | `evaluator.module_graph.acyclicity`; `evaluator.module_graph.allowed_dependency_policy` | Усі п’ять зіставлень `MAP-MODULE-DEPENDENCY-TO-A1-ALLOWED-EDGE-V1` мають результат `UNRESOLVED` — capability не верифіковано |

У таблиці capabilities означають те, що evaluator конфігурує або заявляє перевіряти; у цьому запуску обидва capability inventories мають статус `INCOMPLETE_OR_UNVERIFIED`, а кожна capability має `verification_status=UNVERIFIED`. Реальні evaluator outputs водночас показують `COMPLIANT`, а незалежний source inspection є повним. Ці факти не замінюють окремого доказу повноти capability inventory чи його семантичної придатності для вимоги.

Після переходу A0.4 вимагає Reporting query port (`app.modules.reporting.service` → `app.modules.tasks.public.get_task_summary`) і забороняє попередній приватний імпорт `task_summary`. В A0.3 існував тимчасовий виняток для приватного імпорту, обмежений станами A0.2/A0.3. Module-level allowed edge set не змінився. Кожна вимога та її джерело прив’язані до digest відповідного state manifest.

Інвентар повний лише для оголошених типів manifest-вимог (`COMPLETE_FOR_DECLARED_MANIFEST_TYPES`); повнота всього нормативного requirement universe — `UNKNOWN`. Для обох controls залишилися нерозв’язаними: частковий широкий catalog obligation; інваріанти маніфеста поза scope вибраного evaluator; а також authority status відповідної policy (`DRAFT`, registry `OPEN`, approval source відсутній). Тому декларація policy не використовується як незалежно схвалена вимога, а відсутність додаткового запису не трактується як відсутність вимоги.

## Незалежна перевірка inspection coverage

Verifier відновив очікуваний source scope із точного Git tree, state manifest та окремо pinned evaluator configuration; фактичний scope перевірив за digest-bound evaluator output. У кожному з чотирьох запусків — два evaluators у двох станах — перевірено `31/31` файлів: `missing=0`, `unexpected=0`, `altered=0`, `verified_matching=31`. `AC_PUBLIC_API` має `COMPLETE`; `AC_MODULE_GRAPH` має збіжність статичних relationships і відсутність знайдених циклів, але повнота динамічних edges залишається `UNKNOWN`.

Для `AC_MODULE_GRAPH` реконструйовані статичні imports змінилися з 6 до 7 і збіглися зі спостереженнями. П’ять дозволених module-level edges залишилися незмінними. Статичний аналіз не охоплює dynamic imports, reflection і runtime dependency injection; star-import symbols та imports із composition roots поза `app/modules` також залишаються поза доведеним scope.

## Фактична діагностика адаптації

Обидві оцінки повернули `NOT_EVALUABLE`, `configuration_change_necessity=NOT_EVALUABLE` і `pair_semantic_validity=UNKNOWN`.

- `AC_PUBLIC_API`: `EVALUATOR_CAPABILITY_INVENTORY_NOT_VERIFIED`, `EVALUATOR_CAPABILITY_NOT_VERIFIED`, `INDEPENDENT_REQUIREMENTS_REMAIN_UNRESOLVED`, `NORMATIVE_APPLICABILITY_NOT_APPROVED`, `REQUIREMENT_UNIVERSE_COMPLETENESS_UNKNOWN`.
- `AC_MODULE_GRAPH`: ті самі причини та додатково `DYNAMIC_DEPENDENCY_EDGE_COMPLETENESS_UNKNOWN`.

Отже, цей реальний перехід не підтверджує ані достатність наявних representations (`RETAIN_CANDIDATE`), ані необхідність конкретної зміни конфігурації (`ADAPTATION_NEEDED`). Відсутні докази не дозволяють вибрати дію; це відрізняється від виявленого, але ще не класифікованого mismatch (`MISMATCH_DETECTED`).

## Методичні негативні та регресійні перевірки

- **A — нова незалежна вимога, якої немає в незміненому evaluator:** `test_new_independent_requirement_missing_from_unchanged_evaluator_is_detected` додає source-bound edge `beta→gamma`; діагноз знаходить його в `missing_post_transition_controls`, повертає `NOT_COVERED` для цього mapping і `ADAPTATION_NEEDED`.
- **B — справжнє покриття:** повна незалежна вимога з верифікованою capability дає `RETAIN_CANDIDATE` — лише технічного кандидата.
- **C — неповний інвентар / невирішена authority:** повертається `NOT_EVALUABLE` з точними uncertainty reason codes.
- **D — однакові рядки з evaluator configuration:** вони не можуть підмінити independent requirement source; результат — `NOT_EVALUABLE`.
- **E — невстановлена семантична відповідність:** збіг label не приймається за mapping; результат — `UNRESOLVED` і `NOT_EVALUABLE`.
- **F — регресія реального A0.3 → A0.4:** запускаються справжні observations і поточна класифікація обчислюється заново; код не закріплює `RETAIN_CANDIDATE` як очікуваний результат.

## Метод Ψ, gates та межі висновку

Method Ψ виконався на свіжих A0.4 observations без змін у його коді чи method inputs. Його фактичне рішення — `HOLD`; operation plan містить 0 операцій, prediction не видано, scoring та measurement не виконувалися. `HOLD` містить причини `COST_MODEL_UNRESOLVED`, `MANDATORY_APPLICABILITY_UNKNOWN`, `UNKNOWN_MANDATORY_LINK_PREVENTS_TRANSITION`. Усі 18 applicability лишилися `UNKNOWN`.

Baseline залишається `PROSPECTIVE_RECONSTRUCTION_NOT_HISTORICAL` і `NOT_APPROVED`; policy — `DRAFT_OPEN_UNAPPROVED`; trust scope доказового verifier — `TEST_ONLY`. Залишено без змін `NO_GO`, `P_ALGORITHM_STATUS=NOT_READY`, `G1=INCOMPLETE`, `G4=NOT_AUTHORIZED`, `G-A1-C4-REF-FROZEN=NOT_READY`. Це DEVELOPMENT-валідація реалізації, а не виміряний B0/Ψ результат, approval, незалежний semantic review чи доказ повноти нормативних вимог. Frozen research artifacts та authorization gates не змінювалися.

Архів містить сирі результати, source/config identities, input/output digests та transition readback. Перевірка завантаженого release asset:

```text
shasum -a 256 mono-ci-psi-transition-40282986322-1.zip
d79f53a11a9d60f71c791de74248a55d04fe8dce28df3497af4e9cfd8d8d1cb1

uv run --frozen --extra dev python -m experiments.execution.tooling.mono_ci_b0_psi_archive \
  transition-verify --archive mono-ci-psi-transition-40282986322-1.zip \
  --extract-to <readback-directory>
verification_status: PASS; member_count: 445
```

Наступна межа — незалежно верифікувати evaluator capability inventory у заявленому scope та окремо закрити нормативну authority, applicability, requirement-universe completeness і semantic review. Цей звіт сам по собі їх не встановлює й не просуває жоден research gate.
