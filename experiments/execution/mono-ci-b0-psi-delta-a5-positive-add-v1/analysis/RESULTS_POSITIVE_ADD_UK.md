# Контрольований позитивний експеримент ADD для ΔA5 — результати

- **Study ID:** `MONO_CI_A05_POSITIVE_ADD_TEST_ONLY_V1`
- **Статус технічного виконання:** `COMPLETED`
- **Freeze:** `623057825cdd1d98087f030eb3e7325fbca3edffe1d631bdfc6609426406313e`
- **C0 archive SHA-256:** `76024640bf1a5bfc8771f91a7c9c113c7486f44e28f6290b56dafb32867ae890`
- **C1 repetitions:** `3/3` (warmup: `COMPLETED`)

## Методика

C0 — повторно використаний, без перезапуску, V2 запуск на тому самому переході A0.4→A0.5: Ψ=`HOLD`, план операцій `[]`, кандидат `MATERIALIZED_UNAPPLIED`. Для C1 незмінений Method Ψ отримав авторське TEST_ONLY позначення `AC_DATA_OWNERSHIP` як обов’язкового лише в обмеженій області дослідження; інші рядки канонічного каталогу залишилися `UNKNOWN`. У метод не передавали очікувану операцію або готовий кандидат. Один warmup і три технічні повтори виконувалися через digest-pinned Docker runner після успішного preflight.

Оцінювання кандидатної конфігурації зараховується лише тоді, коли Ψ видав ADD для обов’язку `AC_DATA_OWNERSHIP` із payload представлення `REP_POSITIVE_ADD_AC_DATA_OWNERSHIP`, запис кандидата пройшов перевірку та активний `AC_DATA_OWNERSHIP` фактично виконався на чистому джерелі й контрольованому порушенні. План ADD не змінює загальне рішення Ψ: у цих C1 запусках рішення лишилося HOLD, тому кандидат не приймався і не застосовувався до коду.

## Результати

| Запуск | Фінальне рішення Ψ | План операцій | Кандидат: перевірка/виконання | B0: чисте; негативне джерело | Кандидат: чисте; негативне джерело | Evaluator, чисте/негативне (мс) | Разом (мс) | Ψ (мс) | Перехід (мс) |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| `DEV_PSI_TRANSITION_A05PA_40612830900_1_MEASURED_01` | `HOLD` | ADD obligation AC_DATA_OWNERSHIP → REP_POSITIVE_ADD_AC_DATA_OWNERSHIP | `valid`/виконано | AC_PUBLIC_API=COMPLIANT, AC_MODULE_GRAPH=COMPLIANT; AC_MODULE_GRAPH=COMPLIANT, AC_PUBLIC_API=COMPLIANT | AC_DATA_OWNERSHIP=COMPLIANT, AC_MODULE_GRAPH=COMPLIANT, AC_PUBLIC_API=COMPLIANT; AC_DATA_OWNERSHIP=NON_COMPLIANT/FOREIGN_TABLE_ACCESS, AC_MODULE_GRAPH=COMPLIANT, AC_PUBLIC_API=COMPLIANT | 164.008 / 157.832 | 321.84 | 2683.555 | — |
| `DEV_PSI_TRANSITION_A05PA_40612830900_1_MEASURED_02` | `HOLD` | ADD obligation AC_DATA_OWNERSHIP → REP_POSITIVE_ADD_AC_DATA_OWNERSHIP | `valid`/виконано | AC_PUBLIC_API=COMPLIANT, AC_MODULE_GRAPH=COMPLIANT; AC_MODULE_GRAPH=COMPLIANT, AC_PUBLIC_API=COMPLIANT | AC_DATA_OWNERSHIP=COMPLIANT, AC_MODULE_GRAPH=COMPLIANT, AC_PUBLIC_API=COMPLIANT; AC_DATA_OWNERSHIP=NON_COMPLIANT/FOREIGN_TABLE_ACCESS, AC_MODULE_GRAPH=COMPLIANT, AC_PUBLIC_API=COMPLIANT | 162.788 / 159.657 | 322.445 | 2632.959 | — |
| `DEV_PSI_TRANSITION_A05PA_40612830900_1_MEASURED_03` | `HOLD` | ADD obligation AC_DATA_OWNERSHIP → REP_POSITIVE_ADD_AC_DATA_OWNERSHIP | `valid`/виконано | AC_PUBLIC_API=COMPLIANT, AC_MODULE_GRAPH=COMPLIANT; AC_MODULE_GRAPH=COMPLIANT, AC_PUBLIC_API=COMPLIANT | AC_DATA_OWNERSHIP=COMPLIANT, AC_MODULE_GRAPH=COMPLIANT, AC_PUBLIC_API=COMPLIANT; AC_DATA_OWNERSHIP=NON_COMPLIANT/FOREIGN_TABLE_ACCESS, AC_MODULE_GRAPH=COMPLIANT, AC_PUBLIC_API=COMPLIANT | 163.814 / 155.179 | 318.993 | 2620.134 | — |

У виміряних C1 запусках: `3` містили ADD; `3` кандидатів були фактично виконані в обох умовах; `3` кандидатів зафіксували `FOREIGN_TABLE_ACCESS` у відомому негативному сценарії.
Повний кандидатний критерій одночасно виконано у `3` повтор(ах).

У виміряних C1 кожний окремий ownership evaluator виклик займав 162.788–164.008 мс на чистому та 155.179–159.657 мс на негативному джерелі — нижче за TEST_ONLY бюджет 225 мс на один доданий evaluator-виклик. Сума двох умов становила 318.993–322.445 мс і наведена окремо, не як порівняння з лімітом на один виклик.

## Обговорення та межі висновку

У всіх трьох C1 operation plan незміненої Ψ містив ADD для обов’язку AC_DATA_OWNERSHIP; його payload матеріалізував валідоване активне представлення, яке пройшло обидва evaluator запуски. На чистому джерелі AC_DATA_OWNERSHIP був COMPLIANT, а на контрольованому негативному джерелі виявив FOREIGN_TABLE_ACCESS; обидва B0 evaluators лишилися COMPLIANT у цій негативній умові. Водночас фінальне рішення Ψ у кожному повторі було HOLD через IMPACTED_RETAIN_REASSESSMENT_MISSING, тому ADD не був прийнятий і не застосовувався. Це спостереження стосується лише діагностично виконаного кандидата на заданому TEST_ONLY тесті й не є оцінкою узагальненої точності чи ефективності.

Оцінка політики, обов’язковості, парної семантики, вартості та допустимості кандидата є авторською TEST_ONLY декларацією, не незалежним чи зовнішнім нормативним схваленням. Відомий негативний випадок не дає підстав оцінювати sensitivity/specificity; один архітектурний перехід і три технічні повтори не доводять узагальнення чи статистичну значущість. Канонічний каталог не змінювався; глобальне покриття не обчислювалося. Статуси залишаються `P_ALGORITHM_STATUS=NOT_READY`, `G1=INCOMPLETE`, `G4=NOT_AUTHORIZED`, reference `NOT_READY`, scoring `NOT_EXECUTED`.

Контрольні суми й повний список учасників збережені у перевіреному доказовому архіві.
