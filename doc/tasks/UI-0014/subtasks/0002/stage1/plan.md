# UI-0014-0002 — Проверки CI и свежести индекса

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

- `doc/tests/run.sh --brief` выполняет `validate --brief`, `docs paths --check`, unit/acceptance и `task validate UI-0001`; на подменённом `index.json` падает с кодом 1 до пересборки.
- Обычный `doc/tests/run.sh` после тестов выполняет `index build` в основном checkout, затем `validate` и `index check`.
- `.github/workflows/` отсутствует.
- Отдельной проверки воспроизводимости индекса во временном дереве нет.

## Шаги

1. Исправить `doc/tests/run.sh`: read-only проверки и `index check` до любой пересборки; не пересобирать индекс в основном checkout.
2. Добавить режим локальной/CI-проверки, который копирует проект во временное дерево, строит там индекс и сравнивает результат с проверяемым снимком.
3. Добавить `.github/workflows/` с шагами: установка зависимостей, `index check`, `validate`, `docs paths --check`, unit/acceptance, установка артефакта и проверка воспроизводимости.
4. Добавить тест stale-index: подмена индекса даёт отказ до пересборки, хеши основного checkout не меняются.
5. Синхронизировать `README.md` и `doc/tests/README.md` с новым порядком проверок.

## Выполненная реализация

- `doc/tests/run.sh` стал read-only: default и `--brief` проверяют существующий индекс, не пересобирая его. Добавлены `--index-only`, `--ci` и `--in-copy`.
- `check_index_reproducible` дважды копирует проект через `tar` (исключая `.git`, кеши и артефакты сборки) и строит индекс с `PYTHONHASHSEED=0` и `PYTHONHASHSEED=12345` в разных временных деревьях. Обе сборки сравниваются с `doc/architecture/index.json` и между собой.
- `--in-copy` запускает выбранный режим в изолированной копии; при отсутствии `kilo.jsonc` и наличии идентичного `kilo.jsonc!!!` восстанавливает имя только в копии с предупреждением.
- Добавлен `.github/workflows/ci.yml`: `run.sh --ci`, сборка wheel и установка артефакта вне checkout с проверкой версии и `--root list`.
- `task evidence` принимает ключ ребёнка, поэтому evidence детей фиксируется тем же CLI.
- Acceptance-тесты: stale index, пересборка, зависящая от `PYTHONHASHSEED`, `--in-copy` без изменения checkout, evidence для ключа ребёнка.
- `README.md`, `doc/tests/README.md`, `doc/tools/README.md` и `SPEC-cli-testing` обновлены.

## Проверка

| Команда | Код | Результат |
|---|---|---|
| `python3 -m unittest ...test_index_gate_rejects_stale_index_without_writing -q` | 0 | stale index отклонён до пересборки, дерево не изменилось |
| `python3 -m unittest ...test_index_gate_detects_environment_dependent_rebuild -q` | 0 | пересборка с другим `PYTHONHASHSEED` отклонена |
| `python3 -m unittest ...test_in_copy_gate_tolerates_missing_local_config_without_touching_checkout -q` | 0 | копия прошла, checkout не изменён |
| `python3 -m unittest ...test_evidence_accepts_subtask_key -q` | 0 | evidence записан и перепроверен для ключа ребёнка |
| `bash doc/tests/run.sh --in-copy --index-only` | 0 | `OK: index freshness and reproducibility` |
| `bash doc/tests/run.sh --in-copy --ci` | 0 | индекс, воспроизводимость, пути, unit/acceptance, UI-0001 |

Основной checkout не изменялся: `kilo.jsonc` переименован вне задачи.

## Приёмка

- AC-1: Устаревший индекс приводит к отказу до пересборки; основной checkout проверка не меняет.

### CASE-2 — stale index и воспроизводимость

- **Fixture:** временная копия проекта; `doc/architecture/index.json` приведён в состояние drift; отдельная копия с пересборкой, зависящей от окружения.
- **Действие:** запустить CI-проверку без `index build` в основном checkout.
- **Оракул:** код 1 до пересборки; сообщение указывает на stale index; SHA-256 `index.json` и остальных файлов не меняются.
- **Положительный вариант:** две пересборки с разными `PYTHONHASHSEED` во временных деревьях байт-идентичны `index.json`; основной checkout остаётся неизменным.
- **Отказ:** успешный код при stale index, пересборка в основном checkout, совпадение только одной пересборки или изменение файлов при проверке.

## Риски

- GitHub Actions в песочнице не запускается; проверяется локальный эквивалент и синтаксис YAML.
- Временная копия должна исключать `.git`, кеши и артефакты сборки, но сохранять все входы проверки.
- Нельзя ломать существующий контракт `run.sh --brief`, которым пользуются агенты и предыдущие задачи.
