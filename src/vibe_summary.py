"""RAG generation layer for VibeCheck.

The content-based scorer in ``src/recommender.py`` performs the *retrieval* half
of RAG. This module adds the *generation* half: a Gemma model (served through the
Hugging Face router via the OpenAI-compatible API) rewrites each retrieved song's
score reasons into a friendly one-liner, grounded strictly in the songs that were
actually retrieved.

The HF router does not reliably support strict JSON-schema enforcement, so the
JSON shape is requested in the prompt and parsed defensively; the grounding check
is the real guardrail against malformed or hallucinated output.

Design contract:
- ``generate_blurbs`` never raises to the caller; on any failure (no token, API
  error, unparseable response, or a response that fails the grounding check) it
  returns ``None`` so the UI can fall back to the rule-based reasons.
"""

import json
import os
from typing import Dict, List, Optional, Tuple

Retrieved = List[Tuple[dict, float, str]]

MODEL = "google/gemma-4-31B-it:novita"
BASE_URL = "https://router.huggingface.co/v1"
MAX_TOKENS = 512


def build_prompt(retrieved: Retrieved) -> str:
    """Build the grounded prompt from the retrieved songs.

    Only the retrieved songs and their score reasons are injected — this is the
    grounding boundary. The exact JSON output shape is described here because we
    coax structured output through the prompt (the HF router may not support a
    ``response_format`` schema).
    """
    lines = []
    for song, _score, explanation in retrieved:
        lines.append(
            f'- id {song["id"]}: "{song["title"]}" by {song["artist"]} '
            f"— why it was recommended: {explanation}"
        )
    catalog = "\n".join(lines)
    return (
        "You are VibeCheck, a friendly music assistant. A recommender has already "
        "chosen the songs below for a listener and explained why each one scored well.\n\n"
        "For each song, write ONE short, warm sentence telling the listener why it fits "
        "their vibe, based only on the reasons given. Keep it natural and specific.\n\n"
        "Songs (each with its id):\n"
        f"{catalog}\n\n"
        "Rules:\n"
        "- Write exactly one sentence per song, keyed by the song's id.\n"
        "- Only mention the songs listed above. Do not invent, add, or mention any "
        "other song, artist, or attribute that is not in this list.\n\n"
        "Return ONLY a JSON object with this exact shape (no prose, no markdown):\n"
        '{"summaries": [{"id": <song id>, "blurb": "<one friendly sentence>"}, ...]}\n'
    )


def _extract_json(content: str) -> dict:
    """Pull the JSON object out of a model response, tolerating markdown fences
    or surrounding prose by slicing from the first ``{`` to the last ``}``."""
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("no JSON object found in response")
    return json.loads(content[start : end + 1])


def generate_blurbs(retrieved: Retrieved, client=None) -> Optional[Dict[int, str]]:
    """Generate one grounded one-liner per retrieved song.

    Returns ``{song_id: blurb}`` on success, or ``None`` on ANY failure — no
    token, an API error, an unparseable response, or a response that fails the
    grounding check. The caller falls back to rule-based reasons whenever this
    returns ``None``. This function never raises.
    """
    try:
        if client is None:
            from openai import OpenAI

            client = OpenAI(base_url=BASE_URL, api_key=os.environ["HF_TOKEN"])

        completion = client.chat.completions.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": build_prompt(retrieved)}],
        )

        content = completion.choices[0].message.content
        data = _extract_json(content)
        blurbs = {int(item["id"]): item["blurb"] for item in data["summaries"]}

        if not check_grounding(blurbs, retrieved):
            return None
        return blurbs
    except Exception:
        # Graceful degradation: any failure means "no AI summary this time".
        return None


def check_grounding(blurbs: Dict[int, str], retrieved: Retrieved) -> bool:
    """Return True only if the AI output is grounded in the retrieved songs.

    Two rules, both required:
    1. No hallucinated songs — every blurb id is in the retrieved set.
    2. Complete — every retrieved song has exactly one non-empty blurb.

    Since ``blurbs`` is a dict keyed by song id, "exactly one blurb per song"
    reduces to the key sets being equal; non-empty values are checked explicitly.
    """
    retrieved_ids = {song["id"] for song, _score, _explanation in retrieved}
    if set(blurbs.keys()) != retrieved_ids:
        return False
    return all(isinstance(blurb, str) and blurb.strip() for blurb in blurbs.values())
