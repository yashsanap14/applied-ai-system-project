"""
VibeCheck — Streamlit UI over the content-based recommender, with an optional
RAG "AI Vibe Summary" layer.

The deterministic scorer (src/recommender.py) retrieves and ranks songs. When an
API key is available and AI summaries are on, Claude rewrites each song's score
reasons into a friendly one-liner, grounded strictly in the retrieved songs
(src/vibe_summary.py). With no key — or on any AI failure — the app falls back to
the rule-based reasons, so it always works.

Run from the repo root:
    streamlit run streamlit_app.py
"""

import os

import streamlit as st
from dotenv import load_dotenv

from src.recommender import load_songs, recommend_songs
from src.vibe_summary import MODEL, generate_blurbs

load_dotenv()  # load ANTHROPIC_API_KEY from a .env file if present

DATA_PATH = "data/songs.csv"
KEY_PRESENT = bool(os.environ.get("ANTHROPIC_API_KEY"))


@st.cache_data
def get_songs():
    return load_songs(DATA_PATH)


songs = get_songs()
genres = sorted({s["genre"] for s in songs})
moods = sorted({s["mood"] for s in songs})

st.set_page_config(page_title="VibeCheck 1.0", page_icon="🎵", layout="centered")
st.title("🎵 VibeCheck 1.0")
st.caption(
    f"Content-based music recommender — current version (no RAG yet). "
    f"Catalog: {len(songs)} songs."
)

with st.sidebar:
    st.header("Your taste profile")
    genre = st.selectbox("Favorite genre", genres)
    mood = st.selectbox("Favorite mood", moods)
    energy = st.slider("Target energy", 0.0, 1.0, 0.5, 0.05)
    likes_acoustic = st.checkbox("I like acoustic sound", value=False)
    k = st.slider("How many recommendations", 1, 10, 5)

    st.divider()
    use_ai = st.checkbox(
        "✨ Use AI summaries",
        value=KEY_PRESENT,
        help="Rewrite each song's score reasons into a friendly one-liner with Claude. "
        "Falls back to the rule-based reasons if no API key is set.",
    )

user_prefs = {
    "genre": genre,
    "mood": mood,
    "energy": energy,
    "likes_acoustic": likes_acoustic,
}

st.write("**Profile sent to the recommender:**")
st.json(user_prefs)

recs = recommend_songs(user_prefs, songs, k=k)

# RAG generation layer: attempt AI one-liners, grounded to the retrieved songs.
# generate_blurbs() returns None on any failure (no key, API error, or a
# response that fails the grounding check) — the UI then shows rule-based reasons.
blurbs = None
if use_ai:
    with st.spinner("Writing grounded AI vibe summaries…"):
        blurbs = generate_blurbs(recs)

if not use_ai:
    st.caption("🧠 Rule-based mode — AI summaries off.")
elif blurbs is not None:
    st.caption(f"✨ AI summaries on ({MODEL}), grounded to the retrieved songs.")
elif not KEY_PRESENT:
    st.caption(
        "🔑 No API key found — showing rule-based reasons. Set `ANTHROPIC_API_KEY` "
        "(or add a `.env` file) to enable AI summaries."
    )
else:
    st.caption("⚠️ AI summary unavailable right now — showing rule-based reasons.")

st.subheader(f"Top {k} songs for your vibe")
for rank, (song, score, explanation) in enumerate(recs, start=1):
    with st.container(border=True):
        st.markdown(
            f"**{rank}. {song['title']}** — *{song['artist']}*  \n"
            f"Score: `{score:.2f}` / 4.50"
        )
        if blurbs and song["id"] in blurbs:
            st.markdown(f"✨ *{blurbs[song['id']]}*")
        for reason in explanation.split("; "):
            st.write(f"- {reason}")
