# Task API

A CRUD API for managing tasks, built with FastAPI and backed by a SQLite database.

## Why SQLite

SQLite was chosen because it requires no separate database server — the entire database lives in a single file (`tasks.db`) inside the project folder. This makes it ideal for a small project like this one: no installation, no configuration, and the database is created automatically the first time the app runs.

## Where the database is stored

The database file `tasks.db` is created in the project root (same folder as `main.py`) the first time the server starts. A `tasks` table is created automatically if it doesn't exist, and it's seeded with 3 example tasks only if the table is empty.

## Run it

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

API runs at http://localhost:8000
Interactive docs at http://localhost:8000/docs

## Endpoints

| Method | Path          | Description          |
|--------|---------------|-----------------------|
| GET    | /             | API info              |
| GET    | /health       | Health check           |
| GET    | /tasks        | List all tasks         |
| GET    | /tasks/{id}   | Get one task           |
| POST   | /tasks        | Create a task           |
| PUT    | /tasks/{id}   | Update a task           |
| DELETE | /tasks/{id}   | Delete a task           |

## Example

```bash
curl -i -X POST http://localhost:8000/tasks -H "Content-Type: application/json" -d '{"title":"Buy milk"}'
```