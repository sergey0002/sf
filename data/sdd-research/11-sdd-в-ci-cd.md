# SDD в CI/CD: валидация спек, дрейф-детекция, quality gates

Интеграция spec-driven workflow в конвейер доставки. Принцип: **CI — исполнитель,
а не судья** (governance в YAML, CI enforces). Валидация спек — блокирующая:
невалидная спека не доходит до генерации кода.

## 1. Шесть новых стадий пайплайна

| Стадия | Что делает |
|---|---|
| **1. Specification validation** | Синтаксис, семантика, соответствие стандартам |
| **2. Code generation trigger** | Генерация автоматически при коммите/merge спек |
| **3. Generated code validation** | Автоматические quality gates на сгенерированный код |
| **4. Testing integration** | Тесты на соответствие спека↔реализация |
| **5. Quality gates** | Чекпоинты, не пропускающие non-compliant спеки |
| **6. Deployment automation** | Спеки как источник конфигурации деплоя |

## 2. Валидация спек: три уровня

| Уровень | Проверки | Инструменты |
|---|---|---|
| **Синтаксис** | Markdown-линт, структура файлов, наличие обязательных секций | markdownlint, prettier, check-prerequisites.sh (Spec Kit) |
| **Семантика** | Корректность дельт, трассируемость, контракты | `openspec validate`, spectral (OpenAPI), AsyncAPI Validator, GraphQL Inspector |
| **Стандарты** | Соответствие шаблонам, конституции, EARS-нотации | Кастомные линтеры, /speckit.analyze, Kiro Analyze Requirements |

**Что ловит каждый уровень:**
- Синтаксис: битые ссылки (lychee), форматирование, отсутствие файлов (spec/plan/tasks).
- Семантика: дельты ADDED/MODIFIED/REMOVED против текущей спеки; OpenAPI-контракты;
  schema validation failures указывают точный путь проблемы.
- Стандарты: конституция check, EARS-паттерны, обязательные поля требований.

**При падении валидации:** пайплайн блокируется; разработчик получает feedback
(ошибки синтаксиса, отсутствующие поля, breaking changes), исправляет локально,
перекоммичивает — валидация запускается снова.

## 3. Quality gates на сгенерированный код

| Гейт | Инструмент | Что проверяет |
|---|---|---|
| Static analysis | SonarQube | Качество кода, техдолг |
| Security scanning | OWASP ZAP, SAST | Уязвимости |
| Performance | Load/perf тесты | SLA из NFR спек |
| Spec alignment | /speckit.converge, /opsx:verify, drift detector | Код соответствует спеке |
| Contract tests | Pact, schemathesis | Реализация соответствует контрактам |

Проваленные гейты блокируют деплой автоматически.

## 4. Drift detection: непрерывный мониторинг

После деплоя дрейф-детекция сравнивает спеки с задеплоенными API непрерывно.
При обнаружении — feedback loop: обновление спеки или регенерация, в зависимости
от того, какая сторона должна измениться.

**Источники сигналов дрейфа:**
- Schema validation failures (спека не соответствует реальности)
- Contract-test failures (реализация разошлась с контрактом)
- Частота ревизий спек (спека переписывается слишком часто — сигнал проблем)
- Spec/code context ratio (агент работает по сырому коду, а не по спеке)

**Записи контроля (audit trail):**

| Точка контроля | Запись |
|---|---|
| Spec authoring | Draft baseline |
| Spec review gate | Approved baseline: approver + timestamp |
| Guided generation | Generation record: версия спеки + модель |
| Drift detection | Drift log: расхождения и нарушенные клаузы |
| Reconciliation | Reconciliation record: что/кто/почему изменилось |

## 5. Метрики spec-driven пайплайна

| Метрика | Целевые значения |
|---|---|
| **Code generation success rate** | 60%+ (пилот), 75%+ (расширение), 85%+ (зрелость) |
| **Specification quality** | Completeness score, clarity rating (peer review), standards compliance % (автоматический линтинг) |
| **Specification drift rate** | Drift incidents/мес, time to detect, time to resolve |
| **Validation failure rate** | По типам: syntax / semantic / breaking changes — показывает, где улучшать качество спек |

## 6. Breaking changes и версионирование спек

- **Semantic versioning для спек:** major bump при breaking changes — сигнал потребителям
  обновить интеграции.
- **Валидационные гейты** детектят breaking changes и требуют explicit approval
  architecture review.
- **Параллельные версии** во время deprecation — существующие потребители не мигрируют
  принудительно.
- **Уведомление за 3–6 месяцев** до breaking changes.

## 7. Мультиформатные пайплайны

Один пайплайн может поддерживать несколько форматов спек:
- OpenAPI — spectral
- AsyncAPI — AsyncAPI Validator
- GraphQL — GraphQL Inspector
- Gherkin — Cucumber dry-run / tag validation
- OpenSpec дельты — `openspec validate`

Единые стандарты качества — через общие lint-правила и quality gates.

## 8. Безопасность и откат

- **Feature flags** — включение/отключение генерации без редеплоя.
- **Manual overrides** — обход автоматизации для срочных фиксов.
- **Emergency procedures** — инциденты в проде без нового workflow.
- **Rollback strategies** — страховочная сетка при проблемах.
- **Деплой:** staging → approval gate → production; blue-green/canary с мгновенным откатом.

## 9. State machine как наблюдаемость

Состояния workflow (draft → approved → generating → validating → deployed) делают
прогресс измеримым: разработчики видят, где спеки в workflow; падения объяснимы
и локализованы, а не «загадочные» ошибки пайплайна.

---

## Источники

- SoftwareSeni — Integrating Spec-Driven Workflows with CI/CD (6 стадий, метрики, breaking changes)
- Anblicks — CI validators, drift detector, spec/code context ratio
- re-cinq.com — точки контроля и записи (baseline, drift log, reconciliation)
- Augment Code — schema validation в CI как машиночитаемый контракт
