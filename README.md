# 🎵 Music Recommender Simulation

## Project Summary

In this project you will build and explain a small music recommender system.

Your goal is to:

- Represent songs and a user "taste profile" as data
- Design a scoring rule that turns that data into recommendations
- Evaluate what your system gets right and wrong
- Reflect on how this mirrors real world AI recommenders

Replace this paragraph with your own summary of what your version does.

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

## Getting Started

### Setup

1. Create a virtual environment (optional but recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Mac or Linux
   .venv\Scripts\activate         # Windows

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python -m src.main
```

### Running Tests

Run the starter tests with:

```bash
pytest
```

You can add more tests in `tests/test_recommender.py`.

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

---

## Experiments You Tried

Use this section to document the experiments you ran. For example:

- What happened when you changed the weight on genre from 2.0 to 0.5
- What happened when you added tempo or valence to the score
- How did your system behave for different types of users

---

## Limitations and Risks

Summarize some limitations of your recommender.

Examples:

- It only works on a tiny catalog
- It does not understand lyrics or language
- It might over favor one genre or mood

You will go deeper on this in your model card.

---

## Reflection

Read and complete `model_card.md`:

[**Model Card**](model_card.md)

Write 1 to 2 paragraphs here about what you learned:

- about how recommenders turn data into predictions
- about where bias or unfairness could show up in systems like this



