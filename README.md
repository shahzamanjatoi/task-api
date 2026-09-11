# Task API

A simple in-memory CRUD API for managing tasks, built with FastAPI.

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