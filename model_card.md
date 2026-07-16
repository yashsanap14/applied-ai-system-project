# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name  

**VibeCheck 1.0**

---

## 2. Intended Use  

This app suggests songs based on what a listener says they like.

It looks at four things: genre, mood, energy, and whether the listener likes acoustic sound.

It assumes the listener can describe their own taste with those four labels. It does not watch real listening habits, skips, or replays. It only compares stated preferences to song labels.

This is a classroom project, not a real product. It's for learning how recommenders work, not for real users.

**Not intended for:** real music apps, real user data, or any real decision about which songs get more exposure. The catalog is too small and made-up for that.

---

## 3. How the Model Works  

Every song gets points based on how well it matches what you said you like.

- Same genre as your favorite? **+2 points.** That's the biggest bonus.
- Same mood as your favorite? **+1 point.**
- Energy close to what you want? **Up to +1 point.** The closer the energy, the more points. Not just "higher is better."
- You like acoustic sound, and the song is acoustic? **+0.5 bonus points.**

Add up all the points for a song. Do this for every song in the catalog. Sort them highest to lowest. Show the top 5, along with the reasons each one scored what it did.

The starter code had none of this logic yet — every scoring rule above is something I wrote from scratch.

---

## 4. Data  

The catalog has **20 songs**.

Each song has: title, artist, genre, mood, energy, tempo, valence, danceability, and acousticness.

There are **17 different genres**, but most genres only have 1 song. There are **16 different moods**.

I added 10 of the 20 songs myself, so the catalog would cover more genres and moods than the original starter file.

This is a tiny, made-up dataset. There's no audio, no lyrics, and no real listening history — just labels I typed in. A real app would have millions of songs and real behavior data. This one has neither.

---

## 5. Strengths  

It works best when a listener's genre, mood, and energy all point the same way.

Example: someone who wants rock, an intense mood, and high energy always gets "Storm Runner." That's the only rock song in the catalog, and it genuinely fits. That result matched my own gut feeling every time I tested it.

The "reasons" list makes every pick easy to understand. You can always see exactly why a song scored what it did — nothing is a black box.

It doesn't break on weird input. Asking for a mood that doesn't exist in the catalog just quietly skips that point instead of crashing.

---

## 6. Limitations and Bias 

During adversarial testing, I found that the fixed +2.0 genre-match bonus can overwhelm even a wildly mismatched energy value: when given a profile requesting `energy: 0.95` but `likes_acoustic: True`, the system recommended "Old Porch Stories" (energy 0.3, off by 0.65) over "Broken Rules" (energy 0.95, a near-perfect match) purely because "Old Porch Stories" matched the requested genre. This happens because a genre match is worth twice as many points as a perfect energy match, so matching genre alone effectively guarantees a top spot regardless of how badly the song's other attributes fit. The effect is amplified by the catalog itself: 15 of the 17 genres are represented by exactly one song, so for most genre preferences there is no real competition within that genre — the single matching song wins by default and mood/energy differences barely matter. In practice, this creates a filter bubble for genre-loyal listeners (they always get "their" genre's one song regardless of fit) while underserving listeners whose real preference is energy or mood rather than genre, since that signal is structurally too weak to outrank a genre match. I confirmed this with a follow-up experiment that halved the genre weight and doubled the energy weight, which narrowed the gap but didn't fully fix it, since mood's flat +1.0 bonus has the same all-or-nothing problem.

---

## 7. Evaluation  

**Profiles tested:** I ran five taste profiles through `src/main.py` — three baseline ("High-Energy Pop," "Chill Lofi," "Deep Intense Rock") built from internally consistent preferences, plus two adversarial edge cases ("Energetic but Sad," which asks for a mood that doesn't exist anywhere in the catalog, and "Acoustic Speed Paradox," which asks for high energy and an acoustic sound at the same time — two things that never co-occur in this data).

**What I looked for:** whether the #1 result matched my own musical intuition for that profile, whether an unmatched or contradictory preference broke anything, and whether the same handful of songs kept cluttering every top-5 list regardless of what was actually requested.

**What surprised me:** the system never crashed on the edge cases, but it did quietly pick a "wrong-feeling" winner for the acoustic/speed paradox (explained more below), and one specific song — "Broken Rules" — showed up in the top 5 of 4 out of 5 profiles, purely because it's one of only 6 songs in the whole 20-song catalog with energy above 0.8. That's not a scoring bug; it's a sign the catalog is too small and too energy-imbalanced to give every kind of listener real variety.

**Comparing each pair of profiles:**

- **High-Energy Pop vs. Chill Lofi** — these two sit at opposite ends of the energy scale (0.9 vs. 0.3) and asked for different genres/moods entirely. The results moved completely, with zero overlap in their #1 picks ("Sunrise City" vs. "Library Rain"). This makes sense: nothing about the two profiles agrees, so the recommender should send them to entirely different corners of the catalog, and it did.
- **High-Energy Pop vs. Deep Intense Rock** — both want high energy (0.9 and 0.95), but different genres and moods. Both results are energetic tracks, but the genre match completely changed which one: pop preference surfaced "Sunrise City," rock preference surfaced "Storm Runner." This shows genre is doing real work here, not just energy — two "loud" listeners with different genre taste get different songs, which is the intended behavior.
- **Deep Intense Rock vs. Chill Lofi** — opposite on every dimension (genre, mood, and energy). Predictably, this produced the most different pair of result lists of any comparison, with completely disjoint top 5s. This is the easiest case for the system to get right, and it did.
- **High-Energy Pop vs. Energetic but Sad** — same target energy (0.9) and genre (pop), but mood changed from "happy" to "sad" (a mood that doesn't exist in the catalog at all). The top two results barely changed order ("Sunrise City" and "Gym Hero" swapped places), because losing the mood bonus only cost "Sunrise City" 1 point — not enough to change which songs are in the running, just their exact ranking. This shows the system degrades gracefully on an impossible mood request instead of breaking.
- **Chill Lofi vs. Acoustic Speed Paradox** — both want `likes_acoustic: True`, but energy targets are opposite (0.3 vs. 0.95). Chill Lofi cleanly surfaced real lofi/acoustic songs at the top. The paradox profile, which asks for something the data can't actually provide, ended up picking "Old Porch Stories" — a slow folk song — over songs that actually matched the requested high energy, purely because of a genre match. This comparison is the clearest evidence that when a user's preferences contradict the actual structure of the data, the genre bonus can produce a pick that doesn't really satisfy what they asked for.

**Why does "Gym Hero" keep showing up for "Happy Pop" listeners? (explained without code):** Our whole music collection only has two songs actually labeled "pop" — one happy ("Sunrise City") and one intense ("Gym Hero"). When someone says "I want pop music," the system gives a big bonus just for having the right genre label, before it even checks mood. Since there are only two pop songs to choose from, both of them get pulled into the top results almost automatically — even though "Gym Hero" doesn't actually match the "happy" mood the listener asked for. It's like a shop that only stocks two pairs of jeans in your size: even if neither is quite your style, you'll still see both when you filter by "jeans in my size," because there's nothing else in that bin to push them down the list. The fix isn't in the code so much as in the data — with only 20 songs and 2 in the "pop" bucket, there simply isn't enough variety for the system to be picky about mood within a genre.

No numeric metrics beyond the scores already produced by `score_song` — comparisons above are based on reading the actual terminal output from each profile run.

---

## 8. Future Work  

1. **Add way more songs.** Most genres only have one right now, so there's no real choice within them.
2. **Give genres partial credit.** "Pop" and "indie pop" should count as somewhat similar, not a hard 0 like two totally unrelated genres.
3. **Add a second, real signal.** Something like "other similar listeners liked this too" (collaborative filtering), instead of relying only on song labels someone typed in by hand.

---

## 9. Personal Reflection  

My biggest learning moment was the "Acoustic Speed Paradox" test. I asked for high energy and an acoustic sound at the same time. The system picked a slow folk song over a real high-energy song, just because the genre matched. Seeing that happen with real numbers made the idea of "bias" click in a way that just reading about it never did.

AI tools helped me build and test this fast. They wrote the CSV loader, the scoring function, and the ranking logic in minutes, and helped me design "adversarial" test profiles I wouldn't have thought of on my own, like a listener who wants something "energetic but sad." But I had to double-check the claims myself by actually running the code and reading the real scores. A couple of times an explanation sounded convincing, but the printed numbers told a slightly different story — so I learned to trust the terminal output over any explanation of it.

What surprised me most is how simple this actually is. It's just a few if-statements and one line of subtraction (`1 - abs(difference)`). No machine learning, no training data, no real users. Yet it still "feels" like it understands your taste, at least a little. That's a strange thing to sit with, knowing real apps like Spotify are doing something conceptually similar under the hood, just at a much bigger scale with real behavior data instead of made-up labels.

If I kept going, I'd want to try adding a real collaborative-filtering signal, and see how the recommendations change once the catalog is bigger than 20 songs.
