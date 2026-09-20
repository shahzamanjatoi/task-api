# Task API

A CRUD API for managing tasks, built with FastAPI, backed by PostgreSQL running in Docker, orchestrated with Docker Compose, and secured with Supabase Auth (JWT-based authentication).

## Architecture

- `main.py` — FastAPI routes for both task CRUD and authentication.
- `repository.py` — `TaskRepository` interface + `PostgresRepository` implementation (repository pattern from Assignment 3).
- `models.py` — The `Task` table model.
- `auth.py` — Initializes the Supabase client from environment variables.
- `dependencies.py` — `get_current_user`, a reusable FastAPI dependency that extracts and verifies the Bearer token via Supabase, used to protect routes.

## Setting up environment variables

1. Copy `.env.example` to `.env`:
```bash
   cp .env.example .env
```
2. Fill in your own values:
   - `DATABASE_URL` — your Postgres connection string (matches `docker-compose.yml` defaults if using Docker)
   - `SUPABASE_URL` — from your Supabase project's Settings → API
   - `SUPABASE_KEY` — the `anon` `public` key from the same page

`.env` is gitignored and never committed. Never share your Supabase keys publicly.

## Run it

With Docker (recommended):
```bash
docker compose up
```

Locally (requires Postgres running separately, e.g. via `docker run` or `docker compose up` for just the `db` service):
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

API runs at `http://localhost:8000`. Interactive docs (with Bearer auth support) at `http://localhost:8000/docs`.

## API Reference

| Method | Path                    | Auth required? | Description                          |
|--------|-------------------------|-----------------|---------------------------------------|
| GET    | `/`                     | No              | API info                              |
| GET    | `/health`               | No              | Health check                          |
| GET    | `/public/info`          | No              | Public, unprotected message           |
| GET    | `/protected/profile`    | Yes (Bearer)    | Returns the authenticated user's id, email, created_at |
| GET    | `/protected/dashboard`  | Yes (Bearer)    | Second protected route, proves middleware reusability |
| POST   | `/auth/signup`          | No              | Create a new user account via Supabase |
| POST   | `/auth/login`           | No              | Authenticate and receive access + refresh tokens |
| POST   | `/auth/logout`          | Yes (Bearer)    | Sign out the current session          |
| GET    | `/tasks`                | No*             | List all tasks                        |
| GET    | `/tasks/{id}`           | No*             | Get one task                          |
| POST   | `/tasks`                | No*             | Create a task                         |
| PUT    | `/tasks/{id}`           | No*             | Update a task                         |
| DELETE | `/tasks/{id}`           | No*             | Delete a task                         |

*Task CRUD routes are unprotected in this assignment's scope — the auth work focused on the `/auth/*` and `/protected/*` routes as specified. Protecting task routes with the same `get_current_user` dependency would be a natural next step.

## How authentication works

1. A client calls `POST /auth/signup` or `POST /auth/login` with an email and password. Supabase validates the credentials and (on login) returns a JWT access token and a refresh token.
2. The client includes that token on subsequent requests to protected routes: `Authorization: Bearer <token>`.
3. The `get_current_user` dependency (in `dependencies.py`) extracts the token from the header, verifies it against Supabase via `supabase.auth.get_user(token)`, and either returns the verified user or raises `401`.
4. Any route that needs protection just declares `user=Depends(get_current_user)` — the verification logic lives in exactly one place.

## Example

```bash
curl -i -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"email":"you@example.com","password":"yourpassword"}'
```

```
HTTP/1.1 200 OK
content-type: application/json

{"access_token":"eyJhbGc...","refresh_token":"..."}
```

```bash
curl -i http://localhost:8000/protected/profile -H "Authorization: Bearer eyJhbGc..."
```