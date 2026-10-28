# Післяекспериментальне відновлення архіву

Початковий hosted run: [40612830900](https://github.com/Pan14ek/evofit-bench/actions/runs/40612830900); GitHub Actions artifact 12784690664 (mono-ci-a05-positive-add-40612830900-1), GitHub-reported digest sha256:349f71d4d911f3caef71599aeada74f6d90adb3db49dde6d7751e3469404751c. Pre-run freeze і виміряний код прив’язані до commit 37176a42cc099f1f159dc137b85fe3e32b8290d5.

Hosted run завершив один warmup і три виміряні C1 переходи та завантажив чотири внутрішні transition archives. Створення зовнішнього study receipt зупинилося на закритій JSON Schema перевірці: агрегатор додавав cost.full_transition_wall_ms, якого схема не дозволяє. Загальний wall-clock час переходу не було збережено; у звіті він лишився невідомим.

Цей архів зібрано лише читанням уже завантажених transition archives, pre-run freeze, preflight і C0 release. Method Ψ, evaluators, transition або виміряні повтори не запускалися повторно. Післяекспериментальний агрегатор також враховує штатну семантику P: ADD із target_type=obligation матеріалізує representation із payload.id; у початковому transient summary цей тип операції помилково не зараховувався. Початкові raw operation plans, рішення Ψ та evaluator outputs не змінені.

У кожному C1 Ψ записав HOLD; operation plan містить ADD для AC_DATA_OWNERSHIP, а перевірена ownership representation пройшла чисту та негативну evaluator умови. HOLD залишається фінальним рішенням Ψ: кандидат не застосовувався до коду. Recovery підтверджує лише технічні записи цих трьох повторів у межах цього TEST_ONLY випадку; він не просуває жоден офіційний gate.
