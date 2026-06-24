# TestY TMS — Контекст для работы

## Авторизация
- **URL:** `https://testy.megapolis-it.pro`
- **API:** `/api/v2/swagger/` — Swagger (176 endpoints)
- **Auth:** JWT (Django REST Framework + drf-extensions)
- **Login endpoint:** `POST /api/token/`
- **Request body:** `{"username": "...", "password": "..."}`
- **Response:** `{"access": "eyJ...", "refresh": "eyJ..."}`
- **Auth header:** `Authorization: Bearer <access_token>`

## Креды
- **Login:** `leonidgalockin`
- **Password:** `ihS|4#Ba`
- **Хранятся в:** `.env` (`TESTY_LOGIN`, `TESTY_PASSWORD`)

## Структура API

### Projects (`/api/v2/projects/`)
- GET — список проектов (page, page_size)
- GET `{id}/` — один проект
- POST — создать проект
- PUT `{id}/` — обновить
- DELETE `{id}/` — удалить
- `GET {id}/members/` — участники
- `GET {id}/progress/` — прогресс

### Cases (`/api/v2/cases/`)
- GET — список кейсов (project, suite, status, page, page_size)
- GET `{id}/` — один кейс
- POST — создать кейс
- PUT `{id}/` — обновить
- DELETE `{id}/` — удалить
- GET `{id}/history/` — история изменений
- GET `{id}/tests/` — связанные тесты
- POST `{id}/copy/` — копировать
- POST `{id}/archive/` — архивировать
- GET `/search/` — поиск

**Поля Case:**
```json
{
  "name": "Название",
  "project": 17,
  "suite": {"id": 218, "name": "Add"},
  "setup": "Подготовка",
  "scenario": "Шаги: 1. ...",
  "expected": "Ожидаемый результат",
  "teardown": "Завершение",
  "description": "Доп. описание\nParameters: ...\nRetry: 2",
  "labels": [{"id": 6, "name": "autotest"}],
  "steps": []
}
```

### Suites (`/api/v2/suites/`)
- GET — список сьютов (project, page, page_size)
- GET `{id}/` — одна сьют
- POST — создать сьют
- PUT `{id}/` — обновить
- DELETE `{id}/` — удалить
- GET `{id}/cases/` — кейсы в сьюте
- GET `{id}/descendants-tree/` — потомки
- GET `{id}/ancestors/` — предки
- GET `{id}/breadcrumbs/` — путь
- GET `{id}/plans/` — тест планы
- GET `{id}/tests/` — тесты
- GET `/union/` — объединение
- GET `/descendants-tree/` — дерево
- POST `/copy/` — копировать
- POST `/bulk-update/` — массовое обновление

**Поля Suite:**
```json
{
  "name": "Название",
  "parent": {"id": 219, "name": "Task"},
  "project": 17,
  "description": "Описание",
  "attributes": {}
}
```

### Test Plans (`/api/v2/testplans/`)
- GET — список
- GET `{id}/` — один
- POST — создать
- PUT `{id}/` — обновить
- DELETE `{id}/` — удалить
- GET `{id}/activity/statuses/` — активность
- GET `{id}/histogram/` — гистограмма
- GET `{id}/labels/` — лейблы
- GET `{id}/progress/` — прогресс
- GET `{id}/statistics/` — статистика
- GET `{id}/status/` — статусы
- GET `{id}/suites/` — сьюты
- GET `{id}/tests/` — тесты
- GET `/union/` — объединение
- GET `/descendants-tree/` — дерево

### Results (`/api/v2/results/`)
- GET — список
- GET `{id}/` — один
- POST — создать
- PUT `{id}/` — обновить
- DELETE `{id}/` — удалить
- POST `/archive/restore/` — восстановить из архива

### Tests (`/api/v2/tests/`)
- GET — список
- GET `{id}/` — один
- POST — создать
- PUT `{id}/` — обновить
- DELETE `{id}/` — удалить
- POST `/archive/restore/` — восстановить из архива
- POST `/bulk-update/` — массовое обновление
- GET `{id}/results-union/` — объединение результатов

### Comments (`/api/v2/comments/`)
- GET — список (case, test, page, page_size)
- POST — создать
- PUT `{id}/` — обновить
- DELETE `{id}/` — удалить

### Users (`/api/v2/users/`)
- GET — список
- GET `me/` — текущий пользователь
- POST — создать
- PUT `me/` — обновить себя
- GET `{id}/` — один пользователь
- POST `change-password/` — сменить пароль
- POST `me/avatar/` — загрузить аватар
- DELETE `me/avatar/` — удалить аватар

### Groups (`/api/v2/groups/`)
- GET — список
- GET `{id}/` — один
- POST — создать
- PUT `{id}/` — обновить
- DELETE `{id}/` — удалить

### Labels (`/api/v2/labels/`)
- GET — список
- POST — создать
- PUT `{id}/` — обновить
- DELETE `{id}/` — удалить

### Statuses (`/api/v2/statuses/`)
- GET — список
- POST — создать
- PUT `{id}/` — обновить
- DELETE `{id}/` — удалить

### Custom Attributes (`/api/v2/custom-attributes/`)
- GET — список
- GET `content-types/` — типы контента
- GET `testresult/` — для результатов
- GET `deleted/` — удалённые
- GET `deleted/recover/` — восстановить удалённые
- GET `deleted/remove/` — удалить удалённые навсегда
- PUT `{id}/` — обновить
- DELETE `{id}/` — удалить
- GET `{id}/delete/preview/` — превью удаления

### Notifications (`/api/v2/notifications/`)
- GET — список
- POST `/mark-as/` — отметить как прочитанное
- POST `/disable/` — отключить
- POST `/enable/` — включить
- GET `/settings/` — настройки
- DELETE `{id}/` — удалить

### Attachments (`/api/v2/attachments/`)
- GET — список
- GET `{id}/` — один
- POST — создать
- DELETE `{id}/` — удалить

### System (`/api/v2/system/`)
- GET `statistics/` — статистика
- GET `messages/` — сообщения

### Plugins
- GET `/plugins/` — список плагинов
- `/plugins/allure-uploader-v2/api/configs/` — конфиги allure
- `/plugins/defect-report/api/defect-report/` — defect report
- `/plugins/test-plan-exporter/` — экспорт тест планов

## Типовые сценарии

### Создать тест кейс в сьют
```python
# 1. Найти проект и сьют
# 2. Создать case с полями: name, project, suite, setup, scenario, expected
```

### Создать сьют
```python
# 1. Найти проект
# 2. Создать suite с полями: name, parent (если вложенная), project, description
```

### Поиск кейсов
```
GET /api/v2/cases/search/?q=<query>&project=<id>
```

### Массовые операции
- bulk-update cases, results, tests
- bulk copy suites
- archive/restore

## MCP Сервер
- **Файл:** `testy_mcp.py`
- **Команда:** `python3 testy_mcp.py`
- **Протокол:** JSON-RPC stdin/stdout
- **Инструменты:** login, logout, get_projects, get_cases, create_case, update_case, delete_case, get_suites, create_suite, get_testplans, get_results, get_users, get_comments, и т.д.

