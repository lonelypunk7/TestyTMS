# TestY MCP HTTP Server

HTTP-прокси для TestY Test Management System. Превращает REST-запросы в MCP JSON-RPC вызовы к TestY API.

## Что это

Сервис-прослойка между HTTP-клиентами (браузеры, curl, Postman, CI/CD) и Testy TMS через протокол MCP. Позволяет работать с TestY через familiar HTTP-эндпоинты без необходимости разбираться в JSON-RPC.

**Архитектура:**

```
HTTP Client          MCP HTTP Server        MCP Process        TestY API
     |                        |                     |                |
  REST/JSON  ─────────────►  aiohttp :8765  ─stdin/stdout──►  testy_mcp.py  ─────►  testy.megapolis-it.pro
     ◄─────────────────────   proxy loop          JSON-RPC        stdlib+httpx
```

## Требования

- Python 3.9+
- `aiohttp` — HTTP-сервер
- `httpx` — HTTP-клиент для TestY API
- `python-dotenv` — загрузка `.env`

## Установка

### 1. Копировать `.env`

```bash
cp .env.example .env
```

Открыть `.env` и подставить свои данные:

```ini
TESTY_URL=https://testy.megapolis-it.pro
TESTY_LOGIN=your_login
TESTY_PASSWORD=your_password
```

### 2. Установить зависимости

```bash
pip install aiohttp httpx python-dotenv
```

## Запуск

### Основной сервер

```bash
python3 mcp_http_server.py
```

Сервер запустится на `http://0.0.0.0:8765`.

### CLI-хелпер (для ручных вызовов)

```bash
# Вызов инструмента с аргументами
python3 call_tool.py get_projects '{"page": 1, "page_size": 10}'

# Pipe mode — через stdin
echo '{"method":"tools/call","id":1,"params":{"name":"get_projects","arguments":{"page":1,"page_size":10}}}' \
  | python3 call_tool.py
```

## HTTP API

Все эндпоинты проксируются через `{resource}/{id}`. Поддерживаются все HTTP-методы.

### GET — чтение

```
GET /projects?page=1&page_size=10           → get_projects
GET /projects/17                            → get_project (id=17)
GET /cases?project_id=17&suite_id=5         → get_cases
GET /cases/search?q=smoke                   → search_cases
```

### POST — создание

```
POST /cases          {"name": "...", "project": 17, ...}  → create_case
POST /suites         {"name": "...", "project": 17, ...}  → create_suite
POST /testplans      {"name": "...", "project": 17, ...}  → create_testplan
POST /comments       {"body": "...", "case_id": 42, ...}  → create_comment
```

### PUT — обновление

```
PUT /cases/123    {"name": "Updated name"}  → update_case
PUT /suites/45    {"description": "new"}    → update_suite
```

### DELETE — удаление

```
DELETE /cases/123    → delete_case
DELETE /suites/45    → delete_suite
```

### Health check

```
GET /health
```

## Карта эндпоинтов

| HTTP Path              | MCP Tool          | Описание              |
|------------------------|-------------------|-----------------------|
| `/projects`            | `get_projects`    | Список проектов       |
| `/projects/{id}`       | `get_project`     | Проект по ID          |
| `/cases`               | `get_cases`       | Список тест-кейсов    |
| `/cases/{id}`          | `get_case`        | Кейс по ID            |
| `/suites`              | `get_suites`      | Список сьютов         |
| `/suites/{id}`         | `get_suite`       | Сьют по ID            |
| `/tests`               | `get_tests`       | Список тестов         |
| `/tests/{id}`          | `get_test`        | Тест по ID            |
| `/testplans`           | `get_testplans`   | Список тест-планов    |
| `/testplans/{id}`      | `get_testplan`    | План по ID            |
| `/results`             | `get_results`     | Список результатов    |
| `/results/{id}`        | `get_result`      | Результат по ID       |
| `/users`               | `get_users`       | Список пользователей  |
| `/users/{id}`          | `get_user`        | Пользователь по ID    |
| `/groups`              | `get_groups`      | Список групп          |
| `/groups/{id}`         | `get_group`       | Группа по ID          |
| `/labels`              | `get_labels`      | Список лейблов        |
| `/labels/{id}`         | `get_label`       | Лейбл по ID           |
| `/statuses`            | `get_statuses`    | Список статусов       |
| `/statuses/{id}`        | `get_status`      | Статус по ID          |
| `/comments`            | `get_comments`    | Список комментариев   |
| `/attachments`         | `get_attachments` | Список вложений       |
| `/notifications`       | `get_notifications` | Уведомления         |
| `/search`              | `search_cases`    | Поиск по кейсам       |
| `/health`              | —                 | Health check          |

## Примеры использования

### Получить проекты

```bash
curl http://localhost:8765/projects
```

### Создать тест-кейс

```bash
curl -X POST http://localhost:8765/cases \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Проверка авторизации через MosID",
    "project": 17,
    "suite": {"id": 341, "name": "Smoke"},
    "description": "Цель: проверить авторизацию через MosID",
    "setup": "Предусловия:\nТочка доступа активна.\nУстройство не авторизовано.",
    "is_steps": true,
    "steps": [
      {
        "name": "Подключиться к SSID",
        "scenario": "Пользователь выбирает SSID",
        "expected": "Подключено к Wi-Fi",
        "sort_order": 1
      }
    ],
    "labels": []
  }'
```

### Обновить кейс

```bash
curl -X PUT http://localhost:8765/cases/123 \
  -H "Content-Type: application/json" \
  -d '{"name": "Обновлённое название"}'
```

### Удалить сьют

```bash
curl -X DELETE http://localhost:8765/suites/45
```

## Структура файлов

```
.
├── mcp_http_server.py    # Основной HTTP-сервер (aiohttp + proxy)
├── testy_mcp.py          # MCP JSON-RPC сервер (TestY client)
├── call_tool.py          # CLI-хелпер для ручных вызовов
├── .env.example          # Шаблон переменных окружения
├── .env                  # Конфиденциальные данные (не коммитится)
├── testy_context.md      # Документация API TestY
├── case_rules.md         # Правила создания тест-кейсов
└── README.md             # Этот файл
```

## Готово.
