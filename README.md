# 🎵 Music Recommender Simulation

## Project Summary

This is **VibeCheck**, a small content-based music recommender with an optional **RAG ("AI Vibe Summary") layer** on top.

You give it a taste profile — favorite genre, favorite mood, target energy, and whether you like acoustic sound — and it compares that against a 20-song catalog. Every song gets a score using a simple point system: genre match (+2.0), mood match (+1.0), energy closeness (up to +1.0), and an acoustic bonus (+0.5). It returns the top 5 highest-scoring songs, each with a plain-language list of reasons for why it scored what it did.

I tested it against several taste profiles, including two deliberately contradictory ones, to see how it handles edge cases — and used those tests to find a real bias: songs in rare genres can outrank a much better energy match just by matching genre. The full writeup of the algorithm, evaluation, and limitations is in [`model_card.md`](model_card.md).

As a stretch feature, the app can optionally rewrite each song's score reasons into a friendly one-liner using a Gemma model served via Hugging Face — see [AI Vibe Summary (RAG Stretch Feature)](#ai-vibe-summary-rag-stretch-feature) below.

---

## How The System Works

Real recommender systems like Spotify or YouTube work by turning your listening behavior into signals — what you play, skip, replay, or search for — and comparing those signals either to other users with similar taste (collaborative filtering) or to the attributes of the songs themselves (content-based filtering). Most production systems blend both, but this project focuses purely on the content-based side: instead of learning from thousands of other users, it looks directly at song attributes (genre, mood, energy, acousticness) and compares them to one user's stated preferences. My version prioritizes genre as the strongest signal, since taste in genre tends to be the most stable and identity-driven part of someone's music preference. Mood comes next, since it captures situational preference (chill vs. intense) that can vary even within a favorite genre. Energy is scored by *closeness* to the user's target rather than just "higher is better," since a listener who wants mid-energy music shouldn't be pushed toward the most extreme tracks. Acousticness acts as a lighter, bonus-style signal for users who specifically like acoustic sound.

**Features used:**

- **Song:** `genre`, `mood`, `energy`, `acousticness` (the four attributes that map directly to what `UserProfile` stores; `tempo_bpm`, `danceability`, `valence` are logged in the data but not weighted in the score since they're highly correlated with `energy`/`acousticness` in this catalog)
- **UserProfile:** `favorite_genre`, `favorite_mood`, `target_energy`, `likes_acoustic`

**Algorithm Recipe:**

For each song, `score_song` adds up four rules:

1. **Genre match: +2.0 points** if `song.genre` equals the user's favorite genre, else `0`.
2. **Mood match: +1.0 point** if `song.mood` equals the user's favorite mood, else `0`.
3. **Energy similarity: up to +1.0 point**, computed as `1 - abs(song.energy - user.target_energy)` — the closer the song's energy is to the user's target, the more points it earns, rather than just rewarding "higher energy is always better."
4. **Acousticness bonus: +0.5 points** if the user likes acoustic music and the song's acousticness is above `0.6`, else `0`.

That gives a maximum possible score of **4.5**. `recommend_songs` sorts every song by this total, highest first, and returns the top `k`.

**Potential bias:** because genre carries the heaviest weight (2.0 out of 4.5), this system might over-prioritize genre and filter out great songs that match the user's mood or energy but happen to sit in a different genre bucket. For example, a chill, low-energy jazz song could score lower than a mismatched-mood pop song purely because "pop" matched and "jazz" didn't — even if the mood and energy fit the listener better. Since genre/mood matching here is all-or-nothing (no partial credit for related genres like "pop" vs. "indie pop"), the system can also feel narrow for users whose taste spans adjacent genres rather than one exact label.

---

## AI Vibe Summary (RAG Stretch Feature)

The stretch feature adds a **Retrieval-Augmented Generation (RAG)** layer on top of the recommender, available in the Streamlit app (`streamlit_app.py`). The key idea: the content-based scorer above **is** the retrieval half of RAG — it already picks the most relevant songs and explains why. The new layer is the *generation* half: an LLM rewrites each retrieved song's score reasons into one friendly, natural-language sentence.

**Architecture** — see [`docs/rag_architecture.md`](docs/rag_architecture.md) for the full Mermaid diagram, and [`docs/superpowers/specs/2026-07-29-rag-vibe-summary-design.md`](docs/superpowers/specs/2026-07-29-rag-vibe-summary-design.md) for the design spec (including the amendment documenting the provider switch below).

| Component | Implementation |
|---|---|
| Retrieval | `src/recommender.py` (unchanged) — top-k songs + score reasons |
| Generation | `src/vibe_summary.py` — calls an LLM to rewrite each song's reasons as a one-liner |
| Model | `google/gemma-4-31B-it:novita`, served through the **Hugging Face Inference Router** (`https://router.huggingface.co/v1`) via the OpenAI-compatible client (`openai` package) |
| Grounding check | Every generated blurb must be keyed to a song `id` that was actually retrieved, and every retrieved song must get exactly one non-empty blurb. Fails either rule → the AI output is discarded. |
| Fallback | If there's no `HF_TOKEN`, the API call fails, the response can't be parsed, or grounding fails — the app **falls back to the rule-based score reasons** shown above. The app never crashes and is fully usable with no token. |

**Why grounding, not fact-checking:** the check doesn't verify that each *sentence* is factually accurate — that's unreliable to automate. Instead it verifies the model didn't hallucinate a song that was never retrieved and didn't skip any retrieved song. This is a deliberate, demonstrable trade-off (see [Limitations and Risks](#limitations-and-risks)).

### Enabling it

1. Get a Hugging Face access token (huggingface.co → Settings → Access Tokens — a "Read" token is enough).
2. Create a `.env` file in the project root (already gitignored):

   ```bash
   echo 'HF_TOKEN=hf_your_token_here' > .env
   ```

3. Run the Streamlit app (see [Getting Started](#getting-started) below) and toggle **"Use AI summaries"** in the sidebar.

With no `HF_TOKEN` set, the toggle still works — the app just shows a caption explaining it fell back to rule-based reasons.

---

## Getting Started

### Setup

1. Create a virtual environment (optional but recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Mac or Linux
   .venv\Scripts\activate         # Windows
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the app — two ways:

   **CLI** (core recommender only, no AI summaries):

   ```bash
   python -m src.main
   ```

   **Streamlit** (interactive UI, with the optional AI Vibe Summary layer):

   ```bash
   streamlit run streamlit_app.py
   ```

   The Streamlit app works with no setup — it defaults to rule-based reasons. To enable AI-generated summaries, add an `HF_TOKEN` first (see [AI Vibe Summary](#ai-vibe-summary-rag-stretch-feature) above).

### Running Tests

Run the full test suite with:

```bash
pytest
```

This covers both the core recommender (`tests/test_recommender.py`) and the RAG generation layer (`tests/test_vibe_summary.py`). The RAG tests are fully deterministic and require **no** Hugging Face token or network access — the LLM client is injected as a fake, so `check_grounding`, `build_prompt`, and the success/error/fallback paths of `generate_blurbs` are all exercised offline.

---

## Sample Recommendation Output

Output from running `python -m src.main` against the two taste profiles defined in `src/main.py`:

```
Loading songs from data/songs.csv...
Loaded songs: 20

============================================================
Upbeat pop listener: {'genre': 'pop', 'mood': 'happy', 'energy': 0.8, 'likes_acoustic': False}
============================================================

1. Sunrise City (by Neon Echo) - Score: 3.98
     - genre match: pop (+2.0)
     - mood match: happy (+1.0)
     - energy similarity: 0.82 vs 0.8 (+0.98)

2. Gym Hero (by Max Pulse) - Score: 2.87
     - genre match: pop (+2.0)
     - energy similarity: 0.93 vs 0.8 (+0.87)

3. Rooftop Lights (by Indigo Parade) - Score: 1.96
     - mood match: happy (+1.0)
     - energy similarity: 0.76 vs 0.8 (+0.96)

4. City Lights Anthem (by Trace Motion) - Score: 0.95
     - energy similarity: 0.85 vs 0.8 (+0.95)

5. Night Drive Loop (by Neon Echo) - Score: 0.95
     - energy similarity: 0.75 vs 0.8 (+0.95)

============================================================
Chill lofi listener: {'genre': 'lofi', 'mood': 'chill', 'energy': 0.35, 'likes_acoustic': True}
============================================================

1. Library Rain (by Paper Lanterns) - Score: 4.50
     - genre match: lofi (+2.0)
     - mood match: chill (+1.0)
     - energy similarity: 0.35 vs 0.35 (+1.00)
     - acoustic bonus: acousticness 0.86 (+0.5)

2. Midnight Coding (by LoRoom) - Score: 4.43
     - genre match: lofi (+2.0)
     - mood match: chill (+1.0)
     - energy similarity: 0.42 vs 0.35 (+0.93)
     - acoustic bonus: acousticness 0.71 (+0.5)

3. Focus Flow (by LoRoom) - Score: 3.45
     - genre match: lofi (+2.0)
     - energy similarity: 0.4 vs 0.35 (+0.95)
     - acoustic bonus: acousticness 0.78 (+0.5)

4. Spacewalk Thoughts (by Orbit Bloom) - Score: 2.43
     - mood match: chill (+1.0)
     - energy similarity: 0.28 vs 0.35 (+0.93)
     - acoustic bonus: acousticness 0.92 (+0.5)

5. Coffee Shop Stories (by Slow Stereo) - Score: 1.48
     - energy similarity: 0.37 vs 0.35 (+0.98)
     - acoustic bonus: acousticness 0.89 (+0.5)
```

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or demo video link here -->

### Sample AI Vibe Summary Output

With `HF_TOKEN` set and AI summaries toggled on, a live run against `{genre: pop, mood: happy, energy: 0.8, likes_acoustic: False}` produced these grounded one-liners (each keyed to the retrieved song's id, verified against the score reasons above — no hallucinated songs):

```
Sunrise City   -> "You'll love this happy pop track with an energy level that perfectly matches your vibe."
Gym Hero       -> "This pop song is a great fit since its energy aligns so well with what you enjoy."
Rooftop Lights -> "This one fits your mood with its happy feel and a very similar energy level."
```

---

## Experiments You Tried

### System Evaluation: Baseline & Edge Case Profiles

To evaluate whether the scoring logic behaves sensibly (and to try to "trick" it), I ran three baseline profiles plus two adversarial edge cases through `src/main.py`:

- **High-Energy Pop**, **Chill Lofi**, **Deep Intense Rock** — baseline profiles with internally consistent preferences (genre, mood, and energy all pointing the same direction).
- **Edge Case: Energetic but Sad** — pairs `mood: "sad"` (a mood that does not exist anywhere in the 20-song catalog) with a high target energy, to see if an unmatched mood breaks anything or just degrades gracefully.
- **Edge Case: Acoustic Speed Paradox** — pairs `likes_acoustic: True` with `energy: 0.95`. In this catalog, energy and acousticness are almost perfectly inversely correlated (see the feature analysis earlier in this README), so no song can actually satisfy both preferences at once.

```
Loading songs from data/songs.csv...
Loaded songs: 20

============================================================
High-Energy Pop: {'genre': 'pop', 'mood': 'happy', 'energy': 0.9, 'likes_acoustic': False}
============================================================

1. Sunrise City (by Neon Echo) - Score: 3.92
     - genre match: pop (+2.0)
     - mood match: happy (+1.0)
     - energy similarity: 0.82 vs 0.9 (+0.92)

2. Gym Hero (by Max Pulse) - Score: 2.97
     - genre match: pop (+2.0)
     - energy similarity: 0.93 vs 0.9 (+0.97)

3. Rooftop Lights (by Indigo Parade) - Score: 1.86
     - mood match: happy (+1.0)
     - energy similarity: 0.76 vs 0.9 (+0.86)

4. Storm Runner (by Voltline) - Score: 0.99
     - energy similarity: 0.91 vs 0.9 (+0.99)

5. Broken Rules (by Static Riot) - Score: 0.95
     - energy similarity: 0.95 vs 0.9 (+0.95)

============================================================
Chill Lofi: {'genre': 'lofi', 'mood': 'chill', 'energy': 0.3, 'likes_acoustic': True}
============================================================

1. Library Rain (by Paper Lanterns) - Score: 4.45
     - genre match: lofi (+2.0)
     - mood match: chill (+1.0)
     - energy similarity: 0.35 vs 0.3 (+0.95)
     - acoustic bonus: acousticness 0.86 (+0.5)

2. Midnight Coding (by LoRoom) - Score: 4.38
     - genre match: lofi (+2.0)
     - mood match: chill (+1.0)
     - energy similarity: 0.42 vs 0.3 (+0.88)
     - acoustic bonus: acousticness 0.71 (+0.5)

3. Focus Flow (by LoRoom) - Score: 3.40
     - genre match: lofi (+2.0)
     - energy similarity: 0.4 vs 0.3 (+0.90)
     - acoustic bonus: acousticness 0.78 (+0.5)

4. Spacewalk Thoughts (by Orbit Bloom) - Score: 2.48
     - mood match: chill (+1.0)
     - energy similarity: 0.28 vs 0.3 (+0.98)
     - acoustic bonus: acousticness 0.92 (+0.5)

5. Old Porch Stories (by Willow Creek) - Score: 1.50
     - energy similarity: 0.3 vs 0.3 (+1.00)
     - acoustic bonus: acousticness 0.8 (+0.5)

============================================================
Deep Intense Rock: {'genre': 'rock', 'mood': 'intense', 'energy': 0.95, 'likes_acoustic': False}
============================================================

1. Storm Runner (by Voltline) - Score: 3.96
     - genre match: rock (+2.0)
     - mood match: intense (+1.0)
     - energy similarity: 0.91 vs 0.95 (+0.96)

2. Gym Hero (by Max Pulse) - Score: 1.98
     - mood match: intense (+1.0)
     - energy similarity: 0.93 vs 0.95 (+0.98)

3. Broken Rules (by Static Riot) - Score: 1.00
     - energy similarity: 0.95 vs 0.95 (+1.00)

4. Iron Verdict (by Grave Circuit) - Score: 0.98
     - energy similarity: 0.97 vs 0.95 (+0.98)

5. City Lights Anthem (by Trace Motion) - Score: 0.90
     - energy similarity: 0.85 vs 0.95 (+0.90)

============================================================
Edge Case: Energetic but Sad: {'genre': 'pop', 'mood': 'sad', 'energy': 0.9, 'likes_acoustic': False}
============================================================

1. Gym Hero (by Max Pulse) - Score: 2.97
     - genre match: pop (+2.0)
     - energy similarity: 0.93 vs 0.9 (+0.97)

2. Sunrise City (by Neon Echo) - Score: 2.92
     - genre match: pop (+2.0)
     - energy similarity: 0.82 vs 0.9 (+0.92)

3. Storm Runner (by Voltline) - Score: 0.99
     - energy similarity: 0.91 vs 0.9 (+0.99)

4. Broken Rules (by Static Riot) - Score: 0.95
     - energy similarity: 0.95 vs 0.9 (+0.95)

5. City Lights Anthem (by Trace Motion) - Score: 0.95
     - energy similarity: 0.85 vs 0.9 (+0.95)

============================================================
Edge Case: Acoustic Speed Paradox: {'genre': 'folk', 'mood': 'chill', 'energy': 0.95, 'likes_acoustic': True}
============================================================

1. Old Porch Stories (by Willow Creek) - Score: 2.85
     - genre match: folk (+2.0)
     - energy similarity: 0.3 vs 0.95 (+0.35)
     - acoustic bonus: acousticness 0.8 (+0.5)

2. Midnight Coding (by LoRoom) - Score: 1.97
     - mood match: chill (+1.0)
     - energy similarity: 0.42 vs 0.95 (+0.47)
     - acoustic bonus: acousticness 0.71 (+0.5)

3. Library Rain (by Paper Lanterns) - Score: 1.90
     - mood match: chill (+1.0)
     - energy similarity: 0.35 vs 0.95 (+0.40)
     - acoustic bonus: acousticness 0.86 (+0.5)

4. Spacewalk Thoughts (by Orbit Bloom) - Score: 1.83
     - mood match: chill (+1.0)
     - energy similarity: 0.28 vs 0.95 (+0.33)
     - acoustic bonus: acousticness 0.92 (+0.5)

5. Broken Rules (by Static Riot) - Score: 1.00
     - energy similarity: 0.95 vs 0.95 (+1.00)
```

**What broke / what surprised me:**

- **"Energetic but Sad" degraded gracefully** — since no song has `mood: "sad"`, the mood term contributed 0 for every song and the system fell back to genre + energy, which is the intended behavior for an unmatched category. Nothing crashed, and the top results (`Gym Hero`, `Sunrise City`) are still reasonable "high energy pop" picks.
- **"Acoustic Speed Paradox" exposed a real bias.** `Old Porch Stories` won at rank 1 with a *terrible* energy match (0.35 similarity — the song's actual energy is 0.3 against a 0.95 target) purely because its genre matched "folk." Meanwhile `Broken Rules`, which matches the requested energy almost exactly (0.95 vs 0.95, energy similarity +1.00), came in dead last because it doesn't happen to be folk, chill, or acoustic. This confirms the bias flagged earlier in "How The System Works": the genre weight (+2.0) can outweigh even a wildly mismatched numeric feature, so a user with contradictory preferences gets a recommendation that's arguably "wrong" on the dimension they'd notice most (how energetic the song actually feels).

---

## Limitations and Risks

**Core recommender:**

- It only works on a tiny (20-song) catalog.
- It does not understand lyrics or language.
- It might over-favor genre matches over mood/energy fit (see the bias discussed above and in the edge-case experiments below).

**AI Vibe Summary (RAG layer):**

- Grounding checks that the model didn't hallucinate a song and covered every retrieved song — it does **not** verify that each generated sentence is factually precise about a song's attributes. A blurb could still be a bit generic or slightly off in a way the grounding check can't catch.
- Depends on a third-party model (`google/gemma-4-31B-it` via the Hugging Face router); if the provider is slow, rate-limited, or returns malformed output, the app silently falls back to rule-based reasons rather than showing an error — good for reliability, but it means "no AI summary" and "provider hiccup" look identical to the user.
- No conversation memory — each recommendation request is a single, independent call; the model has no context beyond the songs retrieved for that one request.

You will go deeper on this in your model card.

---

## Reflection

Read and complete `model_card.md`:

[**Model Card**](model_card.md)

Write 1 to 2 paragraphs here about what you learned:

- about how recommenders turn data into predictions
- about where bias or unfairness could show up in systems like this



