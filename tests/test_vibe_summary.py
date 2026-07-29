"""Tests for the RAG vibe-summary generation layer (src/vibe_summary.py).

All tests are deterministic and run without an API key: the Anthropic client is
injected as a fake, matching the graceful-degradation design.
"""

import json
from types import SimpleNamespace

from src.vibe_summary import build_prompt, check_grounding, generate_blurbs


class FakeClient:
    """Stand-in for anthropic.Anthropic. Returns a canned text block, or raises."""

    def __init__(self, text=None, exc=None):
        self._text = text
        self._exc = exc
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        if self._exc is not None:
            raise self._exc
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=self._text)])


def summaries_json(items):
    """Build the structured-output JSON string the model is asked to return."""
    return json.dumps({"summaries": [{"id": i, "blurb": b} for i, b in items]})


def make_retrieved():
    """Two retrieved songs in the (song_dict, score, explanation) shape that
    recommend_songs() returns."""
    return [
        (
            {"id": 1, "title": "Library Rain", "artist": "Paper Lanterns"},
            4.5,
            "genre match: lofi (+2.0); mood match: chill (+1.0)",
        ),
        (
            {"id": 2, "title": "Midnight Coding", "artist": "LoRoom"},
            4.43,
            "genre match: lofi (+2.0)",
        ),
    ]


# --- check_grounding -------------------------------------------------------

def test_check_grounding_accepts_complete_in_set_blurbs():
    retrieved = make_retrieved()
    blurbs = {1: "A rainy lofi pick that matches your chill mood.", 2: "More lofi to code to."}
    assert check_grounding(blurbs, retrieved) is True


def test_check_grounding_rejects_hallucinated_id():
    retrieved = make_retrieved()
    blurbs = {1: "ok", 2: "ok", 99: "this song was never retrieved"}
    assert check_grounding(blurbs, retrieved) is False


def test_check_grounding_rejects_missing_song():
    retrieved = make_retrieved()
    blurbs = {1: "only one of the two songs got a blurb"}
    assert check_grounding(blurbs, retrieved) is False


def test_check_grounding_rejects_empty_blurb():
    retrieved = make_retrieved()
    blurbs = {1: "ok", 2: ""}
    assert check_grounding(blurbs, retrieved) is False


# --- build_prompt ----------------------------------------------------------

def test_build_prompt_includes_each_retrieved_song():
    retrieved = make_retrieved()
    prompt = build_prompt(retrieved)
    for song, _score, explanation in retrieved:
        assert song["title"] in prompt
        assert song["artist"] in prompt
        assert explanation in prompt
        assert f"id {song['id']}" in prompt


def test_build_prompt_instructs_grounding():
    prompt = build_prompt(make_retrieved()).lower()
    # Must tell the model to stay grounded in the listed songs only.
    assert "only" in prompt
    assert "do not" in prompt or "don't" in prompt


# --- generate_blurbs -------------------------------------------------------

def test_generate_blurbs_returns_dict_on_grounded_response():
    retrieved = make_retrieved()
    text = summaries_json([(1, "Rainy lofi that matches your chill mood."),
                           (2, "More lofi to code to.")])
    result = generate_blurbs(retrieved, client=FakeClient(text=text))
    assert result == {
        1: "Rainy lofi that matches your chill mood.",
        2: "More lofi to code to.",
    }


def test_generate_blurbs_returns_none_on_api_error():
    retrieved = make_retrieved()
    result = generate_blurbs(retrieved, client=FakeClient(exc=RuntimeError("boom")))
    assert result is None


def test_generate_blurbs_returns_none_on_ungrounded_response():
    retrieved = make_retrieved()
    # id 99 was never retrieved — grounding must reject the whole response.
    text = summaries_json([(1, "ok"), (99, "a hallucinated song")])
    result = generate_blurbs(retrieved, client=FakeClient(text=text))
    assert result is None
