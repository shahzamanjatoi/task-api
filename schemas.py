from enum import Enum
from pydantic import BaseModel, Field, ValidationError
import json
import re


class Category(str, Enum):
    billing = "billing"
    bug = "bug"
    feature = "feature"
    other = "other"


class Urgency(str, Enum):
    low = "low"
    normal = "normal"
    high = "high"


class SuggestedTeam(str, Enum):
    support = "support"
    engineering = "engineering"
    sales = "sales"


class TriageInput(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


class TriageOutput(BaseModel):
    category: Category
    urgency: Urgency
    suggested_team: SuggestedTeam
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str


def extract_json(text: str) -> str:
    text = text.strip()
    fence_match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end != -1:
        text = text[brace_start:brace_end + 1]
    return text


def parse_and_validate(raw_text: str):
    try:
        json_str = extract_json(raw_text)
        data = json.loads(json_str)
        validated = TriageOutput.model_validate(data)
        return validated, None
    except (json.JSONDecodeError, ValidationError) as e:
        return None, str(e)