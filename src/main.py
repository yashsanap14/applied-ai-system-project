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

    # Two contrasting taste profiles: the target features score_song() compares
    # each song against. Running both side by side shows whether genre/mood
    # matching actually shifts the ranking, instead of energy doing all the work.
    profiles = {
        "Upbeat pop listener": {
            "genre": "pop",
            "mood": "happy",
            "energy": 0.8,
            "likes_acoustic": False,
        },
        "Chill lofi listener": {
            "genre": "lofi",
            "mood": "chill",
            "energy": 0.35,
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
