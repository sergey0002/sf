# UI-0014 — Воспроизводимая установка и CI

Статус: реализовано и проверено; закрытие блокировано зависимостью `UI-0012` и внешним состоянием checkout.
Выпуск дорожной карты: v0.1.
Источник: `nextplan.md` §7, 19 и §24, пакет P04.
Зависимости: `UI-0012`.

## Объём

- pyproject.toml
- .github/workflows/
- doc/tools/
- doc/tests/
- doc/architecture/
- README.md

## Зависимость и снимок

`UI-0012` находится в фазе `verification`: `can_close: true`, но запись ещё не `completed`. Это не мешает подготовке и локальной реализации на проверенном снимке, но блокирует `close` для `UI-0014` до завершения зависимости.

Рабочее дерево содержит незакоммиченные изменения предыдущих пакетов, включая `UI-0012` (`doc/tools/arch/cli/app.py`, `doc/tests/run.sh`, `doc/tests/test_task_identity.py`). Их нельзя сбрасывать или перезаписывать. Базой считается текущий рабочий снимок; в верификации нужно зафиксировать SHA-256 затронутых файлов, а не только `HEAD`.

## Исходный результат

Выполнено на текущем снимке до изменений:

| Команда | Код | Результат |
|---|---|---|
| `python3 -m unittest discover -s doc/tools/tests -q` | 0 | 7 тестов, OK |
| `python3 -m unittest discover -s doc/tests -p 'test_*.py' -q` | 0 | 57 тестов, OK |
| `python3 doc/tools/arch/__main__.py scan --scope all --brief` | 0 | `OK scan: all` |
| `python3 doc/tools/arch/__main__.py index check` | 0 | `Index is current` |
| `python3 doc/tools/arch/__main__.py validate --brief` | 0 | `OK validate: architecture` |
| `python3 doc/tools/arch/__main__.py docs paths --check` | 0 | все пути объявлены |
| `python3 doc/tools/arch/__main__.py --version` | 0 | `arch 1.0.0` |
| `python3 -c "import arch; print(arch.__version__)"` | 0 | `0.2.0` |
| `python3 doc/tools/arch/__main__.py task validate UI-0014` | 0 | карточка валидна |
| `python3 doc/tools/arch/__main__.py task subtask validate UI-0014 0001` | 0 | ребёнок валиден |
| `python3 doc/tools/arch/__main__.py task subtask validate UI-0014 0002` | 0 | ребёнок валиден |

Дефекты baseline:

- `pyproject.toml` и `.github/` отсутствуют;
- `--version` печатает `1.0.0`, а `arch.__version__` равен `0.2.0`; метаданных пакета нет;
- `doc/tests/run.sh` в обычном режиме выполняет `index build` в основном checkout;
- отдельного CI-workflow и проверки воспроизводимости в другом дереве нет.

Отдельно проверено на временной копии: `bash doc/tests/run.sh --brief` обнаруживает подменённый `index.json` и завершается с кодом 1 до пересборки. Обычный режим также падает на acceptance-тестах, но сам содержит шаг пересборки в checkout.

## Правила проекта

| ID и раздел | Правило | Действие | AC / CASE |
|---|---|---|---|
| `nextplan.md` §7, Этап 0 | Нужны `pyproject.toml`, console entry point, зафиксированные зависимости и вывод версии; установка воспроизводится из clean checkout | Добавить пакетные метаданные и entry point, связать версию с метаданными | AC-1 / CASE-1 |
| `nextplan.md` §19, v0.1 | Установка из релизного артефакта; CI без записи в checkout | Проверять установку из wheel/sdist вне исходного дерева; не пересобирать индекс в основном checkout | AC-1, AC-2 / CASE-1, CASE-2 |
| `nextplan.md` §24, P04 | Чистая установка запускает CLI; CI выявляет устаревший индекс до сборки и проверяет воспроизводимость во временном дереве; проверки идут через существующие интерфейсы | Использовать `arch`/`run.sh`, не добавлять новый смысловой механизм | AC-1, AC-2 |
| `ARCH-contract`, §6, строки 759–760 | Индекс строится детерминированно; CI запускает `index check` и падает при drift | Сначала read-only `index check`, пересборка только во временной копии | AC-2 / CASE-2 |
| `ARCH-contract`, §8, строки 810–811 | `index build` — запись, `index check` — проверка без записи, `validate` — полный gate | Сохранить разделение команд и коды выхода | AC-2 / CASE-2 |
| `ARCH-contract`, §7, строка 775 | После изменений запускать CLI-валидацию, полный index/link/schema check | Включить `validate`, `docs paths --check`, `index check` в CI | AC-2 / CASE-2 |
| `VIEW-cli-package`, строки 33–34, 75–78 | `__init__.py` содержит версию пакета; точки входа — `python3 -m arch` и прямой запуск | Сохранить обе точки входа, добавить console script | AC-1 / CASE-1 |
| `REG-cli-command-map`, строки 19–21 | `index build/check` и `validate` остаются отдельными командами | Не менять их семантику; использовать в CI | AC-2 |
| `SPEC-cli-testing`, §10 | CI запускает зависимости, unit/acceptance, `task types`, `task validate`, `docs paths --check` | Отразить актуальные команды в workflow и локальном runner | AC-2 / CASE-2 |

## Проверяемые случаи

### CASE-1 — установка из артефакта (AC-1)

- **Fixture:** временная копия проекта на подготовленном снимке; сборка wheel в отдельном каталоге; отдельный install target вне исходного checkout.
- **Действие:** установить артефакт, выйти из исходного каталога, выполнить `arch --version`, затем команду, читающую runtime-ресурсы проекта, например `arch --root <fixture> list --id ARCH-contract --json`.
- **Оракул:** код 0; `arch --version` совпадает с `importlib.metadata.version` установленного пакета и с `arch.__version__`, из которого `pyproject.toml` берёт версию динамически; CLI не зависит от исходного `doc/tools` в `sys.path`; runtime-команда находит конфигурацию и архитектуру через `--root`.
- **Отказной вариант:** артефакт без метаданных или с другой версией даёт расхождение; отсутствие runtime-ресурсов по `--root` даёт ненулевой код; статическая `version` в `pyproject.toml` ломает unit-контракт.

### CASE-2 — устаревший индекс и воспроизводимость (AC-2)

- **Fixture:** временная копия проекта; в `doc/architecture/index.json` или исходном документе внесено расхождение, делающее индекс устаревшим; отдельная копия с пересборкой, зависящей от окружения.
- **Действие:** запустить `doc/tests/run.sh --index-only` без `index build` в основном checkout; затем повторить на копии, где `index build` меняет результат при другом `PYTHONHASHSEED`.
- **Оракул:** stale index даёт код 1 до любой пересборки; SHA-256 `index.json` и остальных файлов не меняются. На чистом снимке две пересборки с `PYTHONHASHSEED=0` и `PYTHONHASHSEED=12345` в разных временных деревьях байт-идентичны `index.json`. Зависящая от окружения пересборка отклоняется.
- **Отказной вариант:** пересборка в основном checkout, успешный код при stale index или совпадение только одной пересборки считаются провалом.

## Выполненная реализация

1. `0001` — добавлен `pyproject.toml` (`arch-cli`, Python >=3.10, зависимости, package discovery под `doc/tools/`, console script `arch = arch.cli.app:run`). Версия имеет один источник: `dynamic = ["version"]` + `attr = "arch.__version__"`; статическая `version` запрещена unit-тестом. `--version` печатает то же значение. Acceptance-тест собирает wheel, устанавливает в отдельный target и проверяет версию, метаданные и чтение ресурсов через `--root`.
2. `0002` — `doc/tests/run.sh` больше не пересобирает индекс в checkout. `--index-only` выполняет read-only `index check`, затем две пересборки с разными `PYTHONHASHSEED` в разных временных деревьях и сравнивает обе с `index.json` и между собой. `--ci` добавляет тесты и fixture. `--in-copy` переносит выбранный режим в изолированную копию. `.github/workflows/ci.yml` вызывает `run.sh --ci`, собирает wheel и проверяет установленный CLI вне checkout.
3. `task evidence` принимает ключ ребёнка (`UI-0014-0001`), поэтому evidence детей фиксируется тем же CLI-контрактом, что и родителя.
4. Обновлены `README.md`, `doc/tools/README.md`, `doc/tests/README.md` и архитектурные записи.

## Синхронизация архитектуры

| ID и раздел | Изменение | AC / CASE |
|---|---|---|
| `VIEW-cli-package`, «Упаковка» и «Точки входа» | Зафиксированы `pyproject.toml`, динамическая версия из `arch.__version__`, console script и чтение данных через `--root` | AC-1 / CASE-1 |
| `REG-cli-command-map`, «Глобальные параметры» и `task evidence` | `--version` связан с `arch.__version__`; CI проверяет `index check` до пересборки и две пересборки с разными hash seed; evidence принимает ключ ребёнка | AC-1, AC-2 |
| `SPEC-cli-testing`, §7 и §10 | CI-набор приведён к `run.sh --ci`, сборке wheel и установке вне checkout; описаны два hash seed и `--in-copy` | AC-2 / CASE-2 |
| `SPEC-cli-implementation`, §1 | Добавлен установленный entry point и динамическая версия | AC-1 / CASE-1 |

Действующее правило `ARCH-contract` §6 о детерминированной пересборке и CI-проверке `index check` сохранено; изменение контракта не требуется.

## Проверка

Основной checkout не изменялся: `kilo.jsonc` переименован в `kilo.jsonc!!!` вне задачи. Поэтому gate запускается через `--in-copy`, который восстанавливает имя только внутри временной копии. Evidence ниже записан командами `arch task evidence --run` на текущем снимке.

| Команда | Код | Результат |
|---|---|---|
| `python3 doc/tools/arch/__main__.py --version` | 0 | `arch 0.2.0` |
| `python3 -m unittest doc.tools.tests.test_arch.PackagingContractTests -q` | 0 | динамическая версия, console script и зависимости объявлены согласованно |
| `python3 -m unittest ...test_installed_package_reports_metadata_version_and_runtime_resources -q` | 0 | wheel собран, установлен вне checkout, версия и `--root list` совпали |
| `python3 -m unittest ...test_index_gate_rejects_stale_index_without_writing -q` | 0 | stale index отклонён до пересборки, файлы не изменены |
| `python3 -m unittest ...test_index_gate_detects_environment_dependent_rebuild -q` | 0 | пересборка, зависящая от `PYTHONHASHSEED`, отклонена |
| `python3 -m unittest ...test_evidence_accepts_subtask_key -q` | 0 | evidence записан и перепроверен для ключа ребёнка |
| `bash doc/tests/run.sh --in-copy --index-only` | 0 | индекс свежий, две пересборки с разными seed байт-идентичны |
| `bash doc/tests/run.sh --in-copy --ci` | 0 | индекс, воспроизводимость, пути, unit/acceptance, UI-0001 |

## Риски и открытые вопросы

- **Грязное рабочее дерево:** изменения `UI-0012` и параллельных сессий не закоммичены. Работать поверх текущего снимка, сохранять чужие файлы и фиксировать хеши; отдельный worktree от `HEAD` потеряет зависимость.
- **Незакрытая зависимость:** `UI-0012` проверена, но не `completed`; `close` для `UI-0014` останется заблокированным до её закрытия.
- **Внешний блокер checkout:** `kilo.jsonc` переименован в `kilo.jsonc!!!` вне scope. Владелец выбрал не трогать файл; gate выполняется через `--in-copy` с явным предупреждением.
- **Смысл «runtime-ресурсы»:** принято, что это CLI, объявленные зависимости и проектные файлы, читаемые через `--root`. Если владелец требует включать `doc/config`/`doc/architecture` внутрь пакета, это расширяет дизайн и scope.
- **Версия:** единственный источник — `arch.__version__` (`0.2.0`); жёстко зашитый `1.0.0` и статическая версия устранены.
- **CI без сети:** GitHub Actions в песочнице не выполняется; YAML проверен, шаги локально воспроизведены через `run.sh --ci` и сборку/установку wheel. Матрица 3.10/3.12 проверяется только в CI.
- **Артефакты сборки:** сборка и пересборка выполняются во временных копиях; `build/`, `dist/` и `*.egg-info` не попадают в checkout. `.gitignore` вне scope задачи.

## Готовность

Карточки и планы валидны, реализация и проверки выполнены, evidence записан CLI, архитектурные записи синхронизированы. `UI-0014` готов к review; закрытие дополнительно требует завершения `UI-0012` и устранения внешнего состояния checkout.
