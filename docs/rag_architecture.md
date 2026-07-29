# VibeCheck — RAG Architecture

This document describes the planned Retrieval-Augmented Generation (RAG) design for
VibeCheck. The key idea: the existing content-based scorer **is** the retrieval half of
RAG. RAG adds a generation layer (Claude) that writes a natural-language "vibe summary"
**grounded only in the retrieved songs**, plus checks that guard against hallucination.

- **Amber** nodes = where AI results are checked (automated tests + human review).
- **Blue** nodes = new components to build.
- Everything else already exists in the project.

```mermaid
flowchart TD
    %% ---------- User Layer ----------
    subgraph USER["👤 User Layer"]
        UI["CLI / Streamlit UI"]
        U1["Taste profile input<br/>favorite_genre, favorite_mood,<br/>target_energy, likes_acoustic"]
    end

    %% ---------- Knowledge Base ----------
    subgraph KB["📚 Knowledge Base — Retrieval Corpus"]
        DB[("data/songs.csv<br/>20-song catalog<br/>genre, mood, energy, acousticness…")]
    end

    %% ---------- Retrieval Layer ----------
    subgraph RET["🔍 Retrieval Layer — existing scorer"]
        R1["load_songs()<br/>parse CSV → records"]
        R2["score_song() + recommend_songs()<br/>content-based ranking"]
        R3["Top-k songs + score reasons<br/>(the 'retrieved context')"]
    end

    %% ---------- Generation Layer ----------
    subgraph GEN["🤖 Generation Layer — new"]
        G1["Prompt builder<br/>inject ONLY retrieved songs<br/>+ ask for a grounded summary"]
        G2["Claude LLM<br/>claude-haiku-4-5 / claude-sonnet-5"]
        G3["Draft AI vibe summary"]
    end

    %% ---------- Verification ----------
    subgraph VER["✅ Verification & QA — where AI results are checked"]
        V1{"Grounding check<br/>mentions only retrieved<br/>titles / artists?"}
        V2["Automated tests — pytest<br/>• retrieval invariants<br/>• golden-profile snapshots<br/>• faithfulness assertion"]
        V3["👤 Human review<br/>rate: helpful / accurate / grounded"]
    end

    OUT["📤 Final response to user"]

    %% ---------- Data flow ----------
    UI --> U1
    U1 -->|"query"| R2
    DB --> R1 --> R2 --> R3
    R3 -->|"grounded context"| G1 --> G2 --> G3
    G3 --> V1
    V1 -->|"pass"| OUT
    V1 -->|"fail: hallucination →<br/>regenerate or fall back<br/>to rule-based text"| G1
    OUT --> UI

    %% ---------- QA hooks ----------
    V2 -. "asserts on" .-> R2
    V2 -. "checks faithfulness of" .-> G2
    V3 -. "reviews sample of" .-> OUT
    V3 -. "new edge cases feed back into" .-> V2

    classDef verify fill:#fde68a,stroke:#b45309,color:#111;
    classDef new fill:#bfdbfe,stroke:#1d4ed8,color:#111;
    class V1,V2,V3 verify;
    class G1,G2,G3 new;
```

## Component legend

| Component | Status | Role |
|---|---|---|
| **User Layer** | exists | Collects the taste profile (the `UserProfile` fields). |
| **Knowledge Base** — `songs.csv` | exists | The retrieval corpus. The LLM may only reference these 20 songs. |
| **Retrieval Layer** — `score_song` / `recommend_songs` | exists | Ranks the catalog against the profile, returns top-k + score reasons. The "R" in RAG. |
| **Prompt builder** | new | Injects only the retrieved songs + scores into the prompt. Grounding = no hallucination. |
| **Claude LLM** | new | Generates the natural-language "why these fit your vibe" summary. |
| **Verification & QA** | new | Three checkpoints (below). |

## Where AI results get checked

1. **Grounding check (automated, per-request)** — before display, verify every song
   title/artist the LLM mentioned is in the retrieved set. On failure, regenerate or fall
   back to the rule-based explanation.
2. **Automated tests — pytest (offline/CI)** — retrieval invariants (scores ≤ 4.5, sorted,
   top-k correct) plus a faithfulness test over fixed "golden" profiles.
3. **Human-in-the-loop review (periodic)** — a person rates a sample of summaries; failures
   become new golden test cases (the feedback loop from `V3` back into `V2`).
