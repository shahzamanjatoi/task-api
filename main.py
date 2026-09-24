import os
import time
import json as json_module
from datetime import datetime, timezone
import random
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI, APITimeoutError, RateLimitError, APIStatusError
from repository import PostgresRepository
from auth import supabase
from dependencies import get_current_user
from schemas import TriageInput, TriageOutput, Category, Urgency, SuggestedTeam, parse_and_validate

load_dotenv()

app = FastAPI(title="Task API", version="3.0")

security = HTTPBearer()

DATABASE_URL = os.getenv("DATABASE_URL")
repo = PostgresRepository(DATABASE_URL)

llm_client = OpenAI(
    base_url=os.environ["LLM_BASE_URL"],
    api_key=os.environ["LLM_API_KEY"],
    timeout=30.0,
    max_retries=0,  # we handle retries ourselves, not the SDK's default of 2
)

PROMPT_VERSION = "triage-v1"
MAX_CALL_RETRIES = 2


def load_prompt():
    with open("prompts/triage-v1.md", "r") as f:
        return f.read()


def log_cost(model, input_tokens, output_tokens, duration_ms, repaired):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt_version": PROMPT_VERSION,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "duration_ms": duration_ms,
        "repaired": repaired,
    }
    print(f"COST_LOG: {json_module.dumps(entry)}")


def call_model_with_retry(system_prompt: str, user_text: str):
    """Calls the model with timeout + retry on timeouts/429/5xx only. Never retries 400/401/403."""
    attempt = 0
    last_exception = None

    while attempt <= MAX_CALL_RETRIES:
        try:
            start = time.time()
            response = llm_client.chat.completions.create(
                model=os.environ["LLM_MODEL"],
                temperature=0.2,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text},
                ],
            )
            duration_ms = int((time.time() - start) * 1000)
            usage = response.usage
            return response.choices[0].message.content, usage, duration_ms

        except APITimeoutError as e:
            last_exception = e
            wait = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(wait)
            attempt += 1

        except RateLimitError as e:
            last_exception = e
            retry_after = getattr(e.response.headers, "get", lambda k: None)("Retry-After") if hasattr(e, "response") else None
            wait = float(retry_after) if retry_after else (2 ** attempt) + random.uniform(0, 1)
            time.sleep(wait)
            attempt += 1

        except APIStatusError as e:
            if e.status_code >= 500:
                last_exception = e
                wait = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(wait)
                attempt += 1
            else:
                # 400, 401, 403, etc — never retry, fail fast
                raise

    raise last_exception


def quarantine(input_text: str, raw_output: str, error: str):
    os.makedirs("logs", exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt_version": PROMPT_VERSION,
        "input": input_text,
        "raw_output": raw_output,
        "error": error,
    }
    with open("logs/quarantine.jsonl", "a") as f:
        f.write(json_module.dumps(entry) + "\n")


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

@app.post("/triage", response_model=TriageOutput)
def triage(input_data: TriageInput):
    if os.getenv("LLM_STUB") == "1":
        return TriageOutput(
            category=Category.other,
            urgency=Urgency.low,
            suggested_team=SuggestedTeam.support,
            confidence=0.5,
            reason="Stub mode: no model was called."
        )

    if os.getenv("LLM_ENABLED", "true").lower() == "false":
        return TriageOutput(
            category=Category.other,
            urgency=Urgency.low,
            suggested_team=SuggestedTeam.support,
            confidence=0.0,
            reason="LLM disabled via kill switch; returning safe fallback."
        )

    system_prompt = load_prompt()

    try:
        raw_text, usage, duration_ms = call_model_with_retry(system_prompt, input_data.text)
    except APITimeoutError:
        raise HTTPException(status_code=504, detail="Model call timed out.")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Model call failed: {str(e)}")

    log_cost(
        model=os.environ["LLM_MODEL"],
        input_tokens=usage.prompt_tokens if usage else None,
        output_tokens=usage.completion_tokens if usage else None,
        duration_ms=duration_ms,
        repaired=False,
    )

    result, error = parse_and_validate(raw_text)
    if result is not None:
        return result

    # Repair retry
    repair_message = (
        f"Your previous answer was rejected for this reason: {error}\n"
        f"Your previous answer was: {raw_text}\n"
        f"Return only corrected JSON matching the schema. No explanation, no code fence."
    )
    try:
        raw_text_retry, usage_retry, duration_ms_retry = call_model_with_retry(system_prompt, repair_message)
    except APITimeoutError:
        raise HTTPException(status_code=504, detail="Model call timed out during repair.")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Model call failed during repair: {str(e)}")

    log_cost(
        model=os.environ["LLM_MODEL"],
        input_tokens=usage_retry.prompt_tokens if usage_retry else None,
        output_tokens=usage_retry.completion_tokens if usage_retry else None,
        duration_ms=duration_ms_retry,
        repaired=True,
    )

    result, error = parse_and_validate(raw_text_retry)
    if result is not None:
        return result

    quarantine(input_data.text, raw_text_retry, error)
    raise HTTPException(
        status_code=422,
        detail="Model could not produce a valid response after one repair attempt."
    )


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