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
    Returns None if it couldn't produce anything usable.
    """
    msgs = [
        {"role": "system", "content": SYNTH_SYSTEM},
        {"role": "user", "content": f"File path: {path}\n\n--- ORIGINAL FILE START ---\n{original}\n--- ORIGINAL FILE END ---\n\nINSTRUCTIONS:\n{instructions}"},
    ]

    resp = client.responses.create(
        model=MODEL,
        messages=msgs,
    )

    # Responses API: prefer output_text when available; else concatenate text parts
    text = ""
    try:
        # new SDKs often expose .output_text
        text = getattr(resp, "output_text", "") or ""
    except Exception:
        pass

    if not text:
        # Fallback to walk output list
        try:
            if hasattr(resp, "output") and isinstance(resp.output, list):
                parts = []
                for item in resp.output:
                    for frag in getattr(item, "content", []) or []:
                        if isinstance(frag, dict) and frag.get("type") == "output_text":
                            parts.append(frag.get("text", ""))
                text = "".join(parts)
        except Exception:
            pass

    text = text.strip()
    if not text:
        return None

    # If the model returned code fences, strip them defensively
    if text.startswith("```"):
        lines = text.splitlines()
        # drop first and last fence lines if present
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    return text or None
