  ![Python](https://img.shields.io/badge/language-Python-blue?logo=python)
  ![db](https://img.shields.io/badge/db-PostgreSQL-blue?logo=PostgreSQL)
  ![contein](https://img.shields.io/badge/contein-Docker-blue?logo=docker)
  ![API](https://img.shields.io/badge/API-FastAPI-green?logo=FastAPI)
  ![License](https://img.shields.io/badge/license-MIT-green)


# Система семантического поиска по базе знаний компании (MVP)

Проект представляет собой ресурс интеллектуального поиска информации в корпоративных документах. В отличие от классического поиска по ключевым словам, система использует алгоритмы <a href="https://ru.wikipedia.org/wiki/%D0%9D%D0%B5%D0%B9%D1%80%D0%BE%D0%BB%D0%B8%D0%BD%D0%B3%D0%B2%D0%B8%D1%81%D1%82%D0%B8%D1%87%D0%B5%D1%81%D0%BA%D0%BE%D0%B5_%D0%BF%D1%80%D0%BE%D0%B3%D1%80%D0%B0%D0%BC%D0%BC%D0%B8%D1%80%D0%BE%D0%B2%D0%B0%D0%BD%D0%B8%D0%B5">NLP</a> (обработки естественного языка) и векторные представления (эмбеддинги) для поиска документов по смысловой близости к запросу пользователя.

## 🛠 Стек технологий

* **Язык:** Python 3.10+
* **ML/NLP:** `sentence-transformers` (PyTorch)
* **База данных:** PostgreSQL
* **Среда разработки:** VS Code
* **Сборка:** Docker
* **API:** FastAPI

---

## Возможности

Публичные:

- **GET `/`** — поисковая страница (поисковая строка + карточки результатов).
- **GET `/api/search?q=...&k=3`** — семантический поиск топ-K (косинусное сходство).
- **GET `/api/documents/count`** — количество документов в базе.
- **GET `/docs`** — Swagger UI.

Только для администратора (HTTP Basic Auth, логин/пароль из `.env`):

- **GET `/admin`** — страница добавления документов (текст или PDF).
- **POST `/api/documents`** — добавление документа (title + content) с автоматической векторизацией.
- **POST `/api/documents/upload`** — загрузка PDF-файла (multipart), извлечение текста и индексация.

Модель эмбеддингов: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (мультиязычная, работает с русским).

## Быстрый старт

### 1. Поднимаем PostgreSQL

```bash
cp .env.example .env
docker compose up -d
```

### 2. Устанавливаем зависимости

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Запускаем сервис

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Открываем [http://localhost:8000](http://localhost:8000) — веб-интерфейс,
или [http://localhost:8000/docs](http://localhost:8000/docs) — Swagger.

### 4. Наполняем базу знаний (только администратор)

Логин/пароль задаются в `.env` (`ADMIN_USER`, `ADMIN_PASSWORD`). Обычные пользователи видят только страницу поиска и не могут добавлять документы.

- **Через веб-интерфейс:** откройте [http://localhost:8000/admin](http://localhost:8000/admin) — браузер спросит логин и пароль. Там две вкладки: добавление текстом и загрузка PDF.
- **Через API:**

  ```bash
  curl -u admin:admin -X POST http://localhost:8000/api/documents \
    -H 'Content-Type: application/json' \
    -d '{"title": "Как оформить отпуск", "content": "Полный текст инструкции...", "block": "HR"}'

  curl -u admin:admin -X POST http://localhost:8000/api/documents/upload \
    -F "file=@instruction.pdf" -F "block=HR"
  ```

При добавлении эмбеддинг считается автоматически и индекс в памяти обновляется — документ сразу доступен для поиска.

## Как это работает

1. При старте приложение загружает все документы и их эмбеддинги из PostgreSQL в NumPy-матрицу (N × 384).
2. Эмбеддинги нормализованы, поэтому косинусное сходство = скалярное произведение — одно матричное умножение `matrix @ query_vec`.
3. Сортируем по убыванию и возвращаем топ-K.
4. При добавлении нового документа индекс в памяти обновляется.

## Структура

```
app/
  api/api.py          — эндпоинты FastAPI
  core/embedder.py    — загрузка модели и функции embed/cosine
  core/logger_setup.py
  db/db.py            — пул asyncpg
  db/requests.py      — DocumentRepo
  static/index.html   — веб-интерфейс (поиск + загрузка документов)
  main.py             — сборка приложения, lifespan, индекс в памяти
init.sql              — схема БД
docker-compose.yml    — Postgres
```

## Требования к окружению

* Python 3.10+
* Docker (для Postgres)
* ~500 МБ на модель при первом запуске
