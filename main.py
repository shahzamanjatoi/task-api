from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlmodel import SQLModel, Field, create_engine, Session, select

app = FastAPI(title="Task API", version="2.0")

# ---- Database model (the actual table) ----
class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    done: bool = False

# ---- Request body model (for creating tasks) ----
class TaskCreate(BaseModel):
    title: str

# ---- Database setup ----
sqlite_file_name = "tasks.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url, echo=False)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def seed_tasks():
    with Session(engine) as session:
        existing = session.exec(select(Task)).first()
        if existing is None:
            session.add(Task(title="Buy groceries", done=False))
            session.add(Task(title="Finish assignment", done=False))
            session.add(Task(title="Walk the dog", done=True))
            session.commit()

@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    seed_tasks()

@app.get("/")
def root():
    return {"name": "Task API", "version": "2.0", "endpoints": ["/tasks"]}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/tasks")
def get_tasks():
    with Session(engine) as session:
        tasks = session.exec(select(Task)).all()
        return tasks

@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    with Session(engine) as session:
        task = session.get(Task, task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return task

@app.post("/tasks", status_code=201)
def create_task(task_data: TaskCreate):
    if not task_data.title or not task_data.title.strip():
        raise HTTPException(status_code=400, detail="Title is required")
    with Session(engine) as session:
        new_task = Task(title=task_data.title, done=False)
        session.add(new_task)
        session.commit()
        session.refresh(new_task)
        return new_task