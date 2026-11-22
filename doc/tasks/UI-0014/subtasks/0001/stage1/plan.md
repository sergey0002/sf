# UI-0014-0001 — Устанавливаемый пакет CLI

Статус: реализовано и проверено; закрытие ожидает `UI-0012`.
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
- Связанные артефакты этой подзадачи

## Исходный результат

- `pyproject.toml` отсутствует; метаданных пакета и console entry point нет.
- `python3 doc/tools/arch/__main__.py --version` печатает `arch 1.0.0`.
- `python3 -c "import arch; print(arch.__version__)"` печатает `0.2.0`.
- `doc/tools/arch/` содержит только Python-модули; отдельных package data нет.
- Точки входа сейчас: `python3 -m arch` из `doc/tools/` и прямой запуск `doc/tools/arch/__main__.py`.

## Шаги

1. Добавить `pyproject.toml`: имя, статическая версия, Python >=3.10, зависимости `PyYAML` и `jsonschema`, package discovery для `doc/tools/arch`, console script `arch`.
2. Связать вывод `--version` с версией пакета; устранить расхождение `1.0.0` / `0.2.0`, не меняя смысл существующих команд.
3. Сохранить обе текущие точки входа и проверить, что установленный console script вызывает тот же `run()`.
4. Добавить проверку соответствия версии `pyproject.toml`, `arch.__version__` и установленных метаданных.
5. Проверить сборку wheel/sdist и установку в чистое окружение вне checkout; зафиксировать результат в `verification.json`.

## Приёмка

- AC-1: CLI запускается из чистой установки и сообщает версию пакета.

### CASE-1 — чистая установка

- **Fixture:** временная копия проекта, wheel в отдельном каталоге, отдельный target вне исходного checkout.
- **Действие:** установить артефакт через `pip install --no-index --no-deps --target`, выполнить `arch --version` из нейтрального cwd, затем `arch --root <fixture> list --id DOC_SAMPLE --json`.
- **Оракул:** код 0; версия в выводе равна `importlib.metadata.version` установленного пакета и версии из `pyproject.toml`; runtime-команда читает проектные ресурсы через `--root`; исходный checkout не изменён.
- **Отказ:** расхождение версий, отсутствие entry point или runtime-ресурсов, запись артефактов сборки в основной checkout.

## Выполненная реализация

- Добавлен `pyproject.toml` с дистрибутивом `arch-cli`, Python >=3.10, зависимостями `PyYAML`/`jsonschema`, package discovery под `doc/tools/` и console script `arch = arch.cli.app:run`.
- Версия имеет один источник: `dynamic = ["version"]` и `[tool.setuptools.dynamic] version = {attr = "arch.__version__"}`. Статическая `version` в `pyproject.toml` отсутствует.
- `arch/cli/app.py` печатает `arch {__version__}` вместо зашитого `1.0.0`.
- `PackagingContractTests` требует динамическую версию, запрещает статическую и проверяет entry point и зависимости.
- Acceptance-тест собирает wheel из временной копии, устанавливает в отдельный target и проверяет версию, метаданные и `--root list`.

## Проверка

| Команда | Код | Результат |
|---|---|---|
| `python3 doc/tools/arch/__main__.py --version` | 0 | `arch 0.2.0` |
| `python3 -m unittest doc.tools.tests.test_arch.PackagingContractTests -q` | 0 | динамическая версия и console script объявлены согласованно |
| `python3 -m unittest ...test_installed_package_reports_metadata_version_and_runtime_resources -q` | 0 | wheel собран, установлен вне checkout, версия и `--root list` совпали |

Основной checkout не изменялся: `kilo.jsonc` переименован вне задачи. Подробности — в родительском плане.

## Риски

- «Runtime-ресурсы» могут означать package data. Принято чтение проектных файлов через `--root`; иное толкование расширяет scope.
- Версия `0.2.0` сохраняется как текущая; смена версии выпуска требует решения владельца.
- Сборка не должна оставлять `build/`, `*.egg-info` или `dist/` в рабочем дереве.
