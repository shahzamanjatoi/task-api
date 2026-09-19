# Task API

A CRUD API for managing tasks, built with FastAPI, backed by PostgreSQL running in Docker, and orchestrated with Docker Compose.

## Architecture

This project uses the **repository pattern** to separate the API layer from the storage layer:

- `main.py` — FastAPI routes. Calls only `repo.get_all()`, `repo.create()`, etc. Contains no SQL or database-specific code.
- `repository.py` — Defines `TaskRepository` (an abstract interface) and `PostgresRepository` (the concrete implementation using SQLModel/Postgres).
- `models.py` — The `Task` table model, shared across the app.

**Honest note on "routes didn't change":** when moving from Assignment 2 (SQLite via SQLModel directly in `main.py`) to this assignment (Postgres via a repository), `main.py` *was* rewritten — the direct `Session`/`select` calls were replaced with repository calls. However, from this point forward, the architecture holds: swapping `PostgresRepository` for a different implementation (e.g., a different database, or an in-memory test double) would require touching only `repository.py`, never `main.py`. That's the actual guarantee this pattern provides.

## Run the whole stack

```bash
docker compose up
```

This starts both Postgres (with a healthcheck so the app waits until the database is actually ready, not just started) and the FastAPI app, connected together. The app is available at `http://localhost:8000`.

To stop everything:
```bash
docker compose down
```

Data persists across `docker compose down` / `docker compose up` because Postgres data is stored in a named Docker volume (`task-postgres-data`), which is separate from the containers themselves.

## Environment variables

Copy `.env.example` to `.env` and fill in real values (or use the defaults matching `docker-compose.yml`):

```bash
cp .env.example .env
```

`.env` is gitignored and never committed — `.env.example` documents the required variable without real credentials.

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