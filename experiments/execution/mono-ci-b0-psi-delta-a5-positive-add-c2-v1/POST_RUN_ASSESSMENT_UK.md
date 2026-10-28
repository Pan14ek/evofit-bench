# Післяекспериментальна оцінка C2 V1: зупинено після warmup

**Статус:** неповне TEST_ONLY спостереження; одного warmup недостатньо для висновку про повторюваність. Три виміряні повтори не виконувалися. Це повідомлення не є перевіреним архівом переходу або завершеним `RESULTS_C2_UK.md`.

## Підсумок C0, C1 та C2

| Умова | Фактичний план Ψ | Рішення Ψ | Кандидат і застосування | Статус доказів |
|---|---|---|---|---|
| **C0** — V2, попередня невирішена умова | Порожній; ADD не було | `HOLD` у warmup і трьох виміряних переходах | Кандидат перевірено на доступних перевірках, але не застосовано | Завершений раніше контрольний запуск: [Actions 40579333932](https://github.com/Pan14ek/evofit-bench/actions/runs/40579333932), [архів V2](https://github.com/Pan14ek/evofit-bench/releases/tag/mono-ci-psi-a05-owner-authorized-v2-40579333932-1) |
| **C1** — позитивний ADD без активних retain reassessments | `ADD AC_DATA_OWNERSHIP` у кожному з трьох виміряних повторів | `HOLD`: `IMPACTED_RETAIN_REASSESSMENT_MISSING` | Кандидат матеріалізовано, перевірено і запущено на чистому та негативному A0.5; governance його не прийняв, конфігурацію не застосовано | Початковий hosted workflow збережено як `FAILURE`; сирі переходи перевірено та опубліковано окремим recovery-релізом нижче |
| **C2 V1** — додати bounded retain умову | У єдиному warmup: порожній план, ADD не було | `HOLD`; `POLICY_CLOSURE_UNVERIFIED`, `UNKNOWN_MANDATORY_LINK_PREVENTS_TRANSITION` та пов’язані причини | Порожні `changes`; кандидат матеріалізовано з наявними двома контролями, але governance не прийняв його. Перевірки цих контролів виконано; прийнятої конфігурації немає | Один raw warmup у GitHub Actions artifact; transition-run schema відхилила запис. Три виміряні повтори не починалися; C2 як завершений експеримент не підтверджений |

`HOLD`, `ADD`, `ACCEPT` і застосування конфігурації — різні результати. У C1 відбувся реальний план `ADD`, але не `ACCEPT`. У C2 під час warmup не було ані `ADD`, ані `ACCEPT`.

## C1: відновлені докази та точна причина HOLD

Окремий recovery-реліз: [C1 post-run recovery release](https://github.com/Pan14ek/evofit-bench/releases/tag/mono-ci-a05-positive-add-recovery-40612830900-1). SHA-256 завантаженого ZIP (21,787,573 bytes), звірений із digest GitHub Release asset:

`3c3aaaa0ab675ec33158cebba9eae565bacab973a09e98ba5e48273952c760a2`

Заморожений C1 пакет: freeze SHA-256 `623057825cdd1d98087f030eb3e7325fbca3edffe1d631bdfc6609426406313e`; код/виконання за commit `37176a42cc099f1f159dc137b85fe3e32b8290d5`. Перевірені source identities: before commit `d3101c0d3aa9b7b709253b6ec7518416f05f65b9`, repository tree `2b436e0aaf09403ea516d73d20a466a122f86592`; after commit `37176a42cc099f1f159dc137b85fe3e32b8290d5`, repository tree `edb25e087f7f2ed3f06ceb165d9bee910f053065`; application tree в обох станах `007196f68652bc13f6798805793ffdfae96f95f7`. Сирі записи підтверджують однаковий план `ADD AC_DATA_OWNERSHIP` з plan SHA-256 `b69eee9b33d3fc1cbc356015e85701fdbc962d5a622fa17f3adbf464001b02ee` у warmup і трьох measured переходах; усі чотири архіви мають `archive_verification=PASS`.

Оригінальний запуск [40612830900](https://github.com/Pan14ek/evofit-bench/actions/runs/40612830900) залишився `FAILURE`: фінальна receipt-перевірка відхилила незадеклароване `cost.full_transition_wall_ms`. Сирі перехідні архіви не змінювали й не перезапускали. Повний час переходу недоступний і тут не відновлюється.

Повторно перевірені freeze, `study-execution.json` (SHA-256 `b2401e64d3f7cf5b07383f1ff5e7ec43bc9e2b16214955dc50d2b5b6646b77ea`), `STUDY_ARCHIVE_MANIFEST.json` та вкладені checksum inventory. Чотири архіви C1 мають успішну повторну перевірку:

| Архів | SHA-256 |
|---|---|
| warmup | `f106446130c6d2c089c702a434ac689404f7fac4b57517bd5b01ab787b642011` |
| measured 01 | `994eaad9e1ee73a76f9a04274bdaf779c2fe902b92bee8807c156cc9784a892d` |
| measured 02 | `b23c35501786b285d5f3961f30953b018062fcf5202694d78e4b5428762fd690` |
| measured 03 | `ac1200e727ecacde345cb2b20272aa2b9b56772ce31ca641020c848f8f533b22` |

Причина C1 `HOLD` — відсутність у фактичному Ψ method input активних retain reassessments для двох зачеплених обов’язків: `AC_PUBLIC_API` і `AC_MODULE_GRAPH`. Це не була відсутність їхніх вихідних файлів, evaluator-ів чи результатів. Окремо збережені C1 докази містили для обох точних пар статус `VALID_TEST_ONLY`, `COMPLIANT`, код завершення `0` та повну статичну інспекцію `31/31`. Їхні digest-и конфігурацій: public API `8853c3a933b23f698c7ba7c5b6e511f292e8d9285dc0de4378741c53e466f7bb`; module graph `1abae6871a477ff2a07685ad645a70defa2f1ac6745598ae4cdc35aab4e95bf6`. Обидва використовували evaluator source manifest `5c17373ba8896ef0c443d826bd0064168ec7c5759c7973f9602b6c2c715b169c`.

Умова C1 вибрала для applicability лише `AC_DATA_OWNERSHIP`; applicability двох retain obligations не була встановлена як активна в тому самому вході Ψ, тому наявні окремі pair outputs не стали активними retain reassessments у його плані. Це розрізняє наявність валідних pair artifacts і їхню придатність як доказу для конкретного переходу. Перевірені результати порівняння:

| Конфігурація | Чистий A0.5 | Негативний ownership probe |
|---|---|---|
| B0 | `AC_PUBLIC_API`, `AC_MODULE_GRAPH`: обидва `COMPLIANT` | Обидва `COMPLIANT`; порушення власності не виявлено |
| Кандидат C1, матеріалізований та випробуваний | Усі три evaluator-и `COMPLIANT`, порушень немає | `AC_DATA_OWNERSHIP`: `NON_COMPLIANT`, `FOREIGN_TABLE_ACCESS`; два попередні evaluator-и `COMPLIANT` |

Кандидат був `valid` та `MATERIALIZED_AND_EXERCISED`, але рішення `HOLD` означало, що його не прийняли й не застосували. Час evaluator-а власності на clean/negative у виміряних повторах наведений нижче.

Час Ψ у трьох C1 виміряних запусках: `2683.555`, `2632.959`, `2620.134 ms`. Час додаткового evaluator `AC_DATA_OWNERSHIP` на clean/negative: `(164.008, 157.832)`, `(162.788, 159.657)`, `(163.814, 155.179) ms`; двоумовні сумарні значення: `321.840`, `322.445`, `318.993 ms`. Повна тривалість переходу C1 недоступна через збій receipt.

## Чи достатньо доказів для bounded retain у C2?

**На рівні точного evaluator–obligation pair у декларованій статичній області — так, як TEST_ONLY технічне свідчення. Для позитивної applicability оцінки й governance переходу в незміненому Ψ — ні.**

У C2 знову підтверджені digest-и конфігурацій, спільний evaluator manifest і незмінність дерева застосунку до/після переходу (`007196f68652bc13f6798805793ffdfae96f95f7`).

Профіль C2 намагався оголосити три обмежені обов’язки у двох станах і створив шість closure claims. Наявний шлях перевірки policy closure у `experiments/execution/tooling/p_applicability.py::_registry_closed_for` приймає рівно один відповідний closure claim для кожного цільового стану. За трьох claims для `before` і трьох для `after` метод повертає `POLICY_CLOSURE_UNVERIFIED`; applicability усіх трьох вибраних обов’язків має `UNKNOWN` в обох станах. Невирішені посилання містять усі шість claim ID і `registry:REGISTRY`.

Застосування `obligation:all` або ширшого `obligation_family` стверджувало б множину, більшу за ці три обрані автором обов’язки, і могло б перетворити сторонні `UNKNOWN` на `INACTIVE`. Це виходить за межі замороженого C2 scope. Наявна політична підстава цього не підтверджує: пілотний реєстр залишається DRAFT/OPEN без production trust anchors, а авторська декларація не змінює його статусу. Отже, за чинним контрактом обґрунтувати C2 із такою bounded applicability не можна. Ми зупинилися, не змінюючи Ψ і не створюючи closure evidence.

## C2 V1 warmup: збережені сирі спостереження

- Запуск: [40648135384](https://github.com/Pan14ek/evofit-bench/actions/runs/40648135384), head `dfab0b8eafcd45addd888ae98c494eb297aca4df`, остаточний статус workflow — `FAILURE`.
- GitHub Actions artifact: `mono-ci-a05-positive-add-c2-40648135384-1`, artifact ID `12798214604`; ZIP SHA-256 `dcc9baf1b8fc7fe1824c834c882138c3d9ae30cee391f255d410644c5185a2ea`. Завантажений ZIP збігся з digest GitHub asset; 548 рядків `SHA256SUMS` для часткового warmup перевірено, розбіжностей немає. [Артефакт доступний у запуску](https://github.com/Pan14ek/evofit-bench/actions/runs/40648135384/artifacts/12798214604).
- Заморожені входи C2: protocol `dcf72ad2939776511ac8338d0443407ec65683b1eca79e0d26469f8faa6abf1e`; profile `9bbbda5ab8d7dc3f60af0e8035bccb0ba7871168ec18a8ee94791d52f465f52a`; freeze `3346ddb8bdc8a4fc80525bac4dbcc1406ee7ecae9f07354582a40c35c0556516`. Перевірка source identity має статус `VERIFIED` (очікувані значення збіглися зі спостереженими): before commit `d3101c0d3aa9b7b709253b6ec7518416f05f65b9`, repository tree `2b436e0aaf09403ea516d73d20a466a122f86592`; after commit `dfab0b8eafcd45addd888ae98c494eb297aca4df`, repository tree `44ff6a07590cd9d7dfd71c12931f481260ce48ad`; дерево застосунку однакове в обох станах `007196f68652bc13f6798805793ffdfae96f95f7`.
- Сирий результат Method Ψ: `d90ac58021a4957cd2d0e528efcc766b6770e2f7d7c48a8df6c68f12c54fbf19`. Operation-plan SHA-256 `ba6e7c2e8dffbb6563f656e2768f06f7033c82670613fc8deb892b2e24813c14`; operations `[]`. Governance повернув `HOLD`; reason codes містили `POLICY_CLOSURE_UNVERIFIED`, `BEFORE_APPLICABILITY_UNRESOLVED`, `MANDATORY_APPLICABILITY_UNKNOWN`, `UNKNOWN_MANDATORY_LINK_PREVENTS_TRANSITION`, `INVARIANT_VERDICTS_NOT_ALL_POSITIVE` та `VERIFIED_GOVERNANCE_PIPELINE_PROOF_MISSING`.
- Docker subprocess Method Ψ: `2,215.011 ms`, exit `0`; digest-pinned image та isolation preflight пройшли. У записі переходу вказано `2,239.152 ms` для поля часу Ψ. Повна тривалість переходу недоступна, бо перевірка переходу не завершилася.
- Digest кандидата `48d2eb0cc8c6de10fd80baf6e7c890ed54d5e8f116d751855d7369feb7c47367`; перевірка — `valid`; список `changes` порожній. Кандидат містить два наявні контролі, але не ADD власності. Статус — `MATERIALIZED_UNAPPLIED`; governance його не прийняв.

Виконавець зупинився після warmup: V6 transition schema відхилила поля C2 evidence ledger (`selected_obligation_ids` не дозволено, а схема очікувала verifier ID від C1). Окрема помилка results schema відхилила `official_boundary`, тому `C2_RESULTS.json` і receipt часткового запуску не були записані. Це помилки readback/receipt, а не позитивний результат Ψ. Жоден виміряний повтор C2 не починався.

### Результати виявлення під час warmup

Ідентичність application tree не змінювалася під час переходу: `007196f68652bc13f6798805793ffdfae96f95f7` (commit до переходу `d3101c0d3aa9b7b709253b6ec7518416f05f65b9`, після — `dfab0b8eafcd45addd888ae98c494eb297aca4df`).

| Перевірена конфігурація / умова | Evaluator-и | Результат |
|---|---|---|
| Наявні контролі B0, чистий A0.5 | `AC_MODULE_GRAPH`, `AC_PUBLIC_API` | Обидва `COMPLIANT`, порушень немає |
| Наявні контролі B0, негативний ownership probe | `AC_MODULE_GRAPH`, `AC_PUBLIC_API` | Обидва `COMPLIANT`, порушень немає: B0 не виявив порушення власності |
| Матеріалізований кандидат C2, чистий A0.5 | Ті самі два контролі | Обидва `COMPLIANT`, порушень немає |
| Матеріалізований кандидат C2, негативний ownership probe | Ті самі два контролі | Обидва `COMPLIANT`, порушень немає: покращення виявлення проти B0 немає |
| Окремий evaluator власності, чистий A0.5 | `AC_DATA_OWNERSHIP` | `COMPLIANT`, порушень немає, `140.900 ms` |
| Окремий evaluator власності, негативний probe | `AC_DATA_OWNERSHIP` | `NON_COMPLIANT`, одне `FOREIGN_TABLE_ACCESS`, `143.745 ms` |

Отже, окремий запуск evaluator власності виявив відомий probe, але цей evaluator не було додано до кандидата; governance не прийняв і не застосував конфігурацію. Авторська межа становила `225 ms` на доданий виклик. Окремо виміряні значення нижчі за цю межу, але це не є виміром додаткової вартості прийнятого кандидата. Час наявних контролів кандидата C2 для module graph/public API становив на clean `139.742/141.730 ms`, а на negative `142.318/144.257 ms`.

Сирі спостереження обмежені заявленою статичною областю інспекції evaluator-ів. Вони не встановлюють незалежно перевіреної семантичної адекватності, загальної ефективності, sensitivity/specificity або статистичної переваги.

## Висновок для монографії

> **C0.** У попередній контрольній умові Method Ψ повернув `HOLD`; операцій адаптації, зокрема `ADD`, не було.
>
> **C1.** У позитивній TEST_ONLY умові Method Ψ сформував фактичний `ADD` для `AC_DATA_OWNERSHIP` у трьох виміряних виконаннях, але governance повернув `HOLD` через відсутність активних retain reassessments для `AC_PUBLIC_API` і `AC_MODULE_GRAPH`. Кандидат було матеріалізовано, перевірено й випробувано на чистому та негативному A0.5, але не прийнято й не застосовано. Повторно перевірені вихідні архіви опубліковано окремо; первісний hosted workflow лишається `FAILURE`, а повний час переходу недоступний.
>
> **C2.** Наявні C1 source-bound evaluator докази підтверджують `COMPLIANT` retain-пари `AC_PUBLIC_API` та `AC_MODULE_GRAPH` у повній 31/31 статичній інспекції. Однак наявний контракт policy closure не може виразити саме bounded множину трьох обов’язків, не поширюючи твердження на ширший каталог. Тому в єдиному збереженому C2 warmup applicability лишилася `UNKNOWN`, Ψ повернув `HOLD` і порожній план. Три виміряні повтори не виконувались; C2 не встановлює позитивного ADD, ACCEPT або застосування конфігурації.
>
> Ці результати описують одну авторськи визначену TEST_ONLY умову. Вони не є незалежною перевіркою семантичної адекватності, узагальненою оцінкою ефективності або статистичним доказом переваги. Межі G1/G4 і `P_ALGORITHM_STATUS` не змінені.

## Рекомендація щодо PR #60

**Не зливати PR #60 у поточному вигляді.** Recovery реліз C1 підтверджений, однак C2 workflow завершився помилкою, а незмінний контракт applicability не може перевірити заявлену bounded closure умову. Для повторного C2 потрібне окреме, явно версійоване вирішення цього контрактного обмеження та виправлення двох V6/results schema помилок; не слід трактувати цей warmup як завершений експеримент.
