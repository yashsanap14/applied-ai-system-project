# VibeCheck RAG — "AI Vibe Summary" Design Spec

**Date:** 2026-07-29
**Status:** Approved (design), pending implementation
**Feature branch:** `rag-vibe-summary`

## Summary

Add a Retrieval-Augmented Generation (RAG) layer to VibeCheck. The existing
content-based scorer (`src/recommender.py`) already performs the *retrieval* half
of RAG — it ranks the 20-song catalog against a user's taste profile and returns
the top-k with score reasons. This feature adds the *generation* half: Claude
rewrites each retrieved song's score reasons into a friendly natural-language
one-liner, grounded strictly in the retrieved songs.

See the architecture diagram in [`docs/rag_architecture.md`](../../rag_architecture.md).

## Locked decisions

| Decision | Choice |
|---|---|
| Surface | Streamlit app only (`streamlit_app.py`) |
| Output shape | Per-song one-liners (one friendly sentence per recommended song) |
| Model | `claude-haiku-4-5` (simple rephrasing task; cheapest tier) |
| Graceful degradation | **First-class** — the app runs and is fully usable with no API key |
| Call style | One-shot (non-streaming); output is ~5 short sentences |

## Non-goals

- No change to `src/recommender.py` (retrieval already works).
- No CLI integration (`src/main.py` stays as-is).
- No semantic fact-checking of each generated sentence (see Grounding rule).
- No embedding-based retrieval — the deterministic scorer is the retriever.

## Architecture

One new module, **`src/vibe_summary.py`**, holds the entire generation layer.
`streamlit_app.py` calls it; `src/recommender.py` is untouched.

Three small, independently testable functions:

- `build_prompt(retrieved) -> str` — builds the grounded prompt, injecting **only**
  the retrieved songs and their score reasons.
- `generate_blurbs(retrieved, client=None) -> dict[int, str] | None` — calls Claude,
  returns `{song_id: one_liner}`, or **`None`** on any failure (never raises to the UI).
  Accepts an optional injected client for testing.
- `check_grounding(blurbs, retrieved) -> bool` — validates the AI output.

*Rationale (separate module + structured output vs. free-text parsing):* isolates the
LLM boundary, makes each piece unit-testable, and reduces grounding to a set check
instead of fragile string parsing.

### Data flow

```
UserProfile ──▶ recommender.recommend_songs() ──▶ top-k songs + score reasons
                                                        │
                                                        ▼
                                      vibe_summary.build_prompt(retrieved)
                                                        │
                                                        ▼
                              vibe_summary.generate_blurbs()  ── Claude (haiku-4-5)
                                                        │
                                                        ▼
                              vibe_summary.check_grounding(blurbs, retrieved)
                                          │pass                    │fail
                                          ▼                        ▼
                                 show AI one-liners        show rule-based reasons
```

## The Claude call

- Model `claude-haiku-4-5`, one-shot (non-streaming), `max_tokens = 512`.
- **No `thinking` and no `output_config.effort`** — Haiku 4.5 does not support the
  `effort` parameter, and the task needs no extended thinking.
- **Structured output** via `output_config.format` (JSON schema): Claude returns a
  list of `{"id": <int>, "blurb": <str>}` objects keyed to the retrieved song IDs.
  This is what makes grounding a trivial set check.
- Prompt rule (in the system/user prompt): *"Write one friendly sentence per song,
  grounded only in the reasons given. Do not mention any song that is not in this list."*
- Client constructed zero-arg (`anthropic.Anthropic()`) so it resolves credentials
  from `ANTHROPIC_API_KEY`, a `.env` file, or an `ant auth login` profile.

## Grounding rule (exact)

Accept the AI output only if **both** hold:

1. **No hallucinated songs** — every returned `id` is in the retrieved ID set.
2. **Complete** — every retrieved song has exactly one blurb.

If either fails → discard AI output → fall back to rule-based reasons.

We deliberately do **not** attempt semantic fact-checking of each sentence against
song attributes — that is unreliable to automate. ID-membership + completeness is the
robust, demonstrable rule and directly matches the "grounding check" node in the
architecture diagram.

## Fallback behavior (first-class)

The app **always** renders the existing rule-based score reasons. The AI one-liner
*replaces* them for a song only when generation succeeds AND passes grounding.

Three degradation triggers, all producing the same result (rule-based reasons + a
status caption):

1. **No credentials** — no `ANTHROPIC_API_KEY` / `.env` / `ant` profile → don't call.
2. **API error** — authentication, rate limit, connection, API status, or a `refusal`
   stop reason → caught, logged, degraded.
3. **Grounding failure** — per the grounding rule above.

The app never crashes and is fully gradeable with no key.

## Key handling & dependencies

- Zero-arg `anthropic.Anthropic()`; optional `.env` loaded via `python-dotenv`.
- **Add to `requirements.txt`:** `anthropic`, `python-dotenv`.
- **Add to `.gitignore`:** `.env`.
- Never hardcode a key.

## UI (streamlit_app.py)

- After the ranked list, an **"AI Vibe Summary"** area: each recommended song shows
  its AI one-liner when available, with the score breakdown still visible beneath.
- A status caption shows the mode: "✨ AI summaries on" / "rule-based (no API key)" /
  "AI unavailable — showing reasons".
- A sidebar toggle **"Use AI summaries"** (default on when a key is present) lets a
  grader switch AI on/off to compare.

## Testing (deterministic, no live API)

All tests run without a key, matching the graceful-degradation ethos. The Anthropic
client is mocked/injected.

- `check_grounding`: hallucinated ID → rejected; missing song → rejected; complete +
  in-set → accepted.
- `build_prompt`: contains every retrieved song and none outside the retrieved set.
- Pipeline with a **mocked** client: canned grounded response → passes through;
  hallucinated response → falls back (returns `None` / rule-based).
- Fallback: a client that raises an API error → `generate_blurbs` returns `None`.

## Config

- `MODEL = "claude-haiku-4-5"`, `MAX_TOKENS = 512` as module constants in
  `src/vibe_summary.py`.

## Scope check

One new module, two dependency additions, additive UI changes to the existing
Streamlit app, and a focused keyless test suite. No changes to the recommender.
Small enough for a single implementation pass.
