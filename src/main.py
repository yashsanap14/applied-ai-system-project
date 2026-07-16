"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

from src.recommender import load_songs, recommend_songs


def main() -> None:
    songs = load_songs("data/songs.csv")
    print(f"Loaded songs: {len(songs)}")

    # Baseline taste profiles: the target features score_song() compares each
    # song against. Running several side by side shows whether genre/mood
    # matching actually shifts the ranking, instead of energy doing all the work.
    profiles = {
        "High-Energy Pop": {
            "genre": "pop",
            "mood": "happy",
            "energy": 0.9,
            "likes_acoustic": False,
        },
        "Chill Lofi": {
            "genre": "lofi",
            "mood": "chill",
            "energy": 0.3,
            "likes_acoustic": True,
        },
        "Deep Intense Rock": {
            "genre": "rock",
            "mood": "intense",
            "energy": 0.95,
            "likes_acoustic": False,
        },
        # Edge case: mood "sad" does not exist anywhere in the catalog, and it's
        # paired with a high target energy - a contradictory, "hyped but sad"
        # request. Checks that an unmatched mood degrades gracefully to
        # genre + energy scoring instead of breaking.
        "Edge Case: Energetic but Sad": {
            "genre": "pop",
            "mood": "sad",
            "energy": 0.9,
            "likes_acoustic": False,
        },
        # Edge case: likes_acoustic=True combined with a near-max target energy.
        # In this catalog, energy and acousticness are almost perfectly inversely
        # correlated, so no song can satisfy both - checks whether the acoustic
        # bonus and energy-similarity terms fight each other in a sensible way.
        "Edge Case: Acoustic Speed Paradox": {
            "genre": "folk",
            "mood": "chill",
            "energy": 0.95,
            "likes_acoustic": True,
        },
    }

    for label, user_prefs in profiles.items():
        recommendations = recommend_songs(user_prefs, songs, k=5)

        print(f"\n{'=' * 60}")
        print(f"{label}: {user_prefs}")
        print(f"{'=' * 60}")
        for rank, (song, score, explanation) in enumerate(recommendations, start=1):
            print(f"\n{rank}. {song['title']} (by {song['artist']}) - Score: {score:.2f}")
            for reason in explanation.split("; "):
                print(f"     - {reason}")


if __name__ == "__main__":
    main()
