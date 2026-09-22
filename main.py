import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI
from repository import PostgresRepository
from auth import supabase
from dependencies import get_current_user
from schemas import TriageInput, TriageOutput, Category, Urgency, SuggestedTeam

load_dotenv()

app = FastAPI(title="Task API", version="3.0")

security = HTTPBearer()

DATABASE_URL = os.getenv("DATABASE_URL")
repo = PostgresRepository(DATABASE_URL)

llm_client = OpenAI(
    base_url=os.environ["LLM_BASE_URL"],
    api_key=os.environ["LLM_API_KEY"],
)


def load_prompt():
    with open("prompts/triage-v1.md", "r") as f:
        return f.read()


class TaskCreate(BaseModel):
    title: str


class TaskUpdate(BaseModel):
    title: str
    done: bool


class AuthCredentials(BaseModel):
    email: str
    password: str


@app.on_event("startup")
def on_startup():
    repo.create_tables()
    repo.seed_if_empty()
    print("Server running and connected to Supabase")


@app.get("/")
def root():
    return {"name": "Task API", "version": "3.0", "endpoints": ["/tasks"]}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/public/info")
def public_info():
    return {"message": "Welcome stranger! This info is public."}


@app.get("/protected/profile")
def protected_profile(user=Depends(get_current_user), _=Depends(security)):
    return {
        "id": user.id,
        "email": user.email,
        "created_at": user.created_at
    }


@app.get("/protected/dashboard")
def protected_dashboard(user=Depends(get_current_user), _=Depends(security)):
    return {
        "message": f"Welcome to your dashboard, {user.email}",
        "id": user.id
    }


# ---- Triage endpoint (Week 7 assignment) ----

@app.post("/triage")
def triage(input_data: TriageInput):
    if os.getenv("LLM_STUB") == "1":
        return TriageOutput(
            category=Category.other,
            urgency=Urgency.low,
            suggested_team=SuggestedTeam.support,
            confidence=0.5,
            reason="Stub mode: no model was called."
        )

    system_prompt = load_prompt()

    response = llm_client.chat.completions.create(
        model=os.environ["LLM_MODEL"],
        temperature=0.2,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": input_data.text},
        ],
    )

    raw_text = response.choices[0].message.content
    print(f"Raw model output: {raw_text}")
    return {"raw_output": raw_text}


# ---- Task CRUD routes (unchanged from A3) ----

@app.get("/tasks")
def get_tasks():
    return repo.get_all()


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    task = repo.get_by_id(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.post("/tasks", status_code=201)
def create_task(task_data: TaskCreate):
    if not task_data.title or not task_data.title.strip():
        raise HTTPException(status_code=400, detail="Title is required")
    return repo.create(task_data.title)


@app.put("/tasks/{task_id}")
def update_task(task_id: int, update: TaskUpdate):
    if not update.title or not update.title.strip():
        raise HTTPException(status_code=400, detail="Title is required")
    task = repo.update(task_id, update.title, update.done)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    deleted = repo.delete(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")


# ---- Auth routes ----

@app.post("/auth/signup", status_code=201)
def signup(credentials: AuthCredentials):
    if not credentials.email or not credentials.password:
        raise HTTPException(status_code=400, detail="Email and password are required")
    try:
        result = supabase.auth.sign_up({
            "email": credentials.email,
            "password": credentials.password
        })
        return {"user": result.user}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/auth/login")
def login(credentials: AuthCredentials):
    if not credentials.email or not credentials.password:
        raise HTTPException(status_code=400, detail="Email and password are required")
    try:
        result = supabase.auth.sign_in_with_password({
            "email": credentials.email,
            "password": credentials.password
        })
        return {
            "access_token": result.session.access_token,
            "refresh_token": result.session.refresh_token
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid login credentials")


@app.post("/auth/logout", status_code=204)
def logout(user=Depends(get_current_user), _=Depends(security)):
    try:
        supabase.auth.sign_out()
    except Exception:
        pass