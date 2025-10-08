# patcher.py
from typing import Optional
from llm import client, MODEL

SYNTH_SYSTEM = (
    "You are a code transformation engine. You will be given the ENTIRE original file and "
    "a set of instructions. Return the FULL UPDATED FILE CONTENT ONLY. "
    "Do not add explanations, comments, or code fences."
)

def synthesize_new_contents(path: str, original: str, instructions: str) -> Optional[str]:
    """
    Ask the model to apply 'instructions' to 'original' and return full new file content (string).
    Returns None if nothing usable is produced.
    """
    def part(role: str, text: str):
        # Responses API uses content parts, not Chat 'messages'
        return {"role": role, "content": [{"type": "input_text", "text": text}]}

    input_msgs = [
        part("system", SYNTH_SYSTEM),
        part(
            "user",
            f"File path: {path}\n\n--- ORIGINAL FILE START ---\n{original}\n--- ORIGINAL FILE END ---\n\nINSTRUCTIONS:\n{instructions}",
        ),
    ]

    resp = client.responses.create(
        model=MODEL,
        input=input_msgs,   # <-- IMPORTANT: use 'input', not 'messages'
        # no temperature here per your note
    )

    # Prefer .output_text if available
    text = getattr(resp, "output_text", "") or ""

    if not text and hasattr(resp, "output") and isinstance(resp.output, list):
        parts = []
        for item in resp.output:
            for frag in getattr(item, "content", []) or []:
                if isinstance(frag, dict) and frag.get("type") == "output_text":
                    parts.append(frag.get("text", ""))
        text = "".join(parts)

    text = (text or "").strip()
    if not text:
        return None

    # Strip accidental code fences
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    return text or None
