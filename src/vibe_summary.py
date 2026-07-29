"""RAG generation layer for VibeCheck.

The content-based scorer in ``src/recommender.py`` performs the *retrieval* half
of RAG. This module adds the *generation* half: Claude rewrites each retrieved
song's score reasons into a friendly one-liner, grounded strictly in the songs
that were actually retrieved.

Design contract:
- ``generate_blurbs`` never raises to the caller; on any failure (no API key,
  API error, or a response that fails the grounding check) it returns ``None``
  so the UI can fall back to the rule-based reasons.
"""

import json
from typing import Dict, List, Optional, Tuple

Retrieved = List[Tuple[dict, float, str]]

MODEL = "claude-haiku-4-5"
MAX_TOKENS = 512

# Structured-output schema: the model must return one {id, blurb} per song.
# Keying by id is what makes the grounding check a simple set comparison.
SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "summaries": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "blurb": {"type": "string"},
                },
                "required": ["id", "blurb"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["summaries"],
    "additionalProperties": False,
}


def build_prompt(retrieved: Retrieved) -> str:
    """Build the grounded prompt from the retrieved songs.

    Only the retrieved songs and their score reasons are injected — this is the
    grounding boundary: the model is told to talk about exactly these songs and
    nothing else.
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
        "other song, artist, or attribute that is not in this list.\n"
    )


def generate_blurbs(retrieved: Retrieved, client=None) -> Optional[Dict[int, str]]:
    """Generate one grounded one-liner per retrieved song.

    Returns ``{song_id: blurb}`` on success, or ``None`` on ANY failure — no
    credentials, an API/refusal error, an unparseable response, or a response
    that fails the grounding check. The caller falls back to rule-based reasons
    whenever this returns ``None``. This function never raises.
    """
    try:
        if client is None:
            import anthropic

            client = anthropic.Anthropic()

        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": build_prompt(retrieved)}],
            output_config={"format": {"type": "json_schema", "schema": SUMMARY_SCHEMA}},
        )

        text = next(
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text"
        )
        data = json.loads(text)
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
