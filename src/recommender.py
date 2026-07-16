import csv
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float

@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool

class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        # TODO: Implement recommendation logic
        return self.songs[:k]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        # TODO: Implement explanation logic
        return "Explanation placeholder"

def load_songs(csv_path: str) -> List[Dict]:
    """Load songs from a CSV file into a list of dicts, with numeric fields converted to float/int."""
    print(f"Loading songs from {csv_path}...")

    songs = []
    with open(csv_path, newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            songs.append({
                "id": int(row["id"]),
                "title": row["title"],
                "artist": row["artist"],
                "genre": row["genre"],
                "mood": row["mood"],
                "energy": float(row["energy"]),
                "tempo_bpm": float(row["tempo_bpm"]),
                "valence": float(row["valence"]),
                "danceability": float(row["danceability"]),
                "acousticness": float(row["acousticness"]),
            })
    return songs

def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """Score a song against user preferences using the Algorithm Recipe, returning (score, reasons)."""
    # Algorithm Recipe: genre match +2.0, mood match +1.0, energy similarity up to
    # +1.0 based on closeness to target energy, acoustic bonus +0.5.
    score = 0.0
    reasons = []

    if song["genre"] == user_prefs["genre"]:
        score += 2.0
        reasons.append(f"genre match: {song['genre']} (+2.0)")

    if song["mood"] == user_prefs["mood"]:
        score += 1.0
        reasons.append(f"mood match: {song['mood']} (+1.0)")

    energy_similarity = 1 - abs(song["energy"] - user_prefs["energy"])
    score += energy_similarity
    reasons.append(f"energy similarity: {song['energy']} vs {user_prefs['energy']} (+{energy_similarity:.2f})")

    if user_prefs.get("likes_acoustic") and song["acousticness"] > 0.6:
        score += 0.5
        reasons.append(f"acoustic bonus: acousticness {song['acousticness']} (+0.5)")

    return score, reasons

def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """Score every song against user preferences and return the top k, ranked highest to lowest."""
    scored = []
    for song in songs:
        score, reasons = score_song(user_prefs, song)
        explanation = "; ".join(reasons)
        scored.append((song, score, explanation))

    ranked = sorted(scored, key=lambda entry: entry[1], reverse=True)
    return ranked[:k]
