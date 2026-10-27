# Монографія: карта вставлення для ΔA5 DEVELOPMENT V1/V2

Цей файл підготовлений для ручного перенесення до наявного Google Doc. Документ напряму не змінювався.

## Методологія експерименту

Вставити опис owner-authorized exploratory DEVELOPMENT V1/V2, точну пару A0.4→A0.5, незмінний B0 та чинну реалізацію Ψ, межі V1/V2, Docker preflight і джерельну прив'язку scope verifier-а. Використовувати перший розділ `OWNER_AUTHORIZED_RESULTS_UK_V2.md` разом із V2 `PROTOCOL_V2.md`. Обов'язково зазначити одну архітектурну одиницю, технічні повтори, TEST_ONLY evidence і незмінні G1/G4 межі.

## Результати дослідження

Вставити V1/V2 таблицю повноти, V2 таблицю фактичних B0/Ψ результатів, таблицю часу й candidate-validation cost, технічні помилки та SVG фігуру з `OWNER_AUTHORIZED_RESULTS_UK_V2.md`, `transition-run-table.csv`, `technical-failures.csv`, `evaluator-samples.csv` і `evaluator-time-distributions.svg`. Окремо зазначити попередній run 40574090499 як wrapper readback failure із збереженими raw HOLD результатами, не об'єднуючи його повтори з новим freeze. У V3 `analysis-summary.json` calibration B0 evaluator process times і transition-level B0 evaluator process times подані окремо; ці дві сукупності не об'єднувати. У таблиці повноти брати planned, measured success/failure, warmups і not-run із sample rows; warmups не зараховувати до measured counts і не підміняти їх legacy aggregate `measured_calls`. Для кожного числового рядка зберегти study `MONO_CI_B0_PSI_DELTA_A5_OWNER_AUTHORIZED_DEV_V2`, workflow run `40579333932`, calibration archive SHA-256 `211cd9bef19c0ad377cc3a01f183b7e062596da9f1a548fe1d71159e502dd837` або відповідний evidence digest і процедуру обробки з `analysis-summary.json`. У V1 частині посилатися на run 40499692594 та archive SHA-256 `d4851c292497728b98af5a75aa8f01883541eb5672274896cf6065cd0c612d27`.

## Обговорення

Вставити фактичні B0/Ψ outcomes і технічні збої з `technical-failures.csv`. Пояснити, що інфраструктурна помилка не є HOLD; HOLD зазначається лише якщо його повернув Method Ψ. Обмежити висновки конкретними статичними evaluators, відомою probe, неповним authority та evidence scope. Не трактувати чотири технічні повтори як незалежні transitions.

## Висновки

Використовувати лише розділ «Запропонований висновок» у `OWNER_AUTHORIZED_RESULTS_UK_V2.md`, замінюючи формулювання за фактичним результатом запуску. Не робити загальних висновків про наукову перевагу, verified mandatory coverage, runtime quality або G1/G4.
