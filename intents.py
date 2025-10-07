from pydantic import BaseModel, Field, ValidationError
from typing import List, Literal, Union, Optional, Dict, Any

class EditFile(BaseModel):
    type: Literal["edit_file"] = "edit_file"
    path: str = Field(..., description="Relative path in the project")
    instructions: str = Field(..., description="High level change description")
    patch: Optional[str] = Field(None, description="Unified diff or direct replacement content")

class CreateFile(BaseModel):
    type: Literal["create_file"] = "create_file"
    path: str
    contents: str

class RunCommand(BaseModel):
    type: Literal["run_command"] = "run_command"
    command: str
    args: List[str] = []


Intent = Union[EditFile, CreateFile, RunCommand]

def intent_json_schema() -> Dict[str, Any]:
    """
    This is the JSON schema for tool parameters.
    We provide a single object with a discriminated `type` field because the
    Responses API function schema does not currently allow `oneOf`.
    """

    return {
        "type": "object",
        "properties": {
            "intent": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["edit_file", "create_file", "run_command"],
                    },
                    "path": {"type": "string"},
                    "instructions": {"type": "string"},
                    "patch": {"type": ["string", "null"]},
                    "contents": {"type": "string"},
                    "command": {"type": "string"},
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": [],
                    },
                },
                "required": ["type"],
                "additionalProperties": False,
            }
        },
        "required": ["intent"],
        "additionalProperties": False,
    }

TOOL_DEFS = [
    {
        "type": "function",
        "name": "emit_intent",
        "description": (
            "Return exactly one structured intent representing the user's request. "
            "Prefer one of: edit_file, create_file, run_command."
        ),
        "parameters": intent_json_schema(),
        "strict": False,
    }
]


def parse_intent(obj: dict) -> Intent:
    """Validate dict -> one of our Intent classes."""
    t = obj.get("type")
    try:
        if t == "edit_file":
            return EditFile(**obj)
        if t == "create_file":
            return CreateFile(**obj)
        if t == "run_command":
            return RunCommand(**obj)
    except ValidationError as ve:
        raise ValueError(str(ve)) from ve
    raise ValueError(f"Unknown or missing intent type: {t}")



