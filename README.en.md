*[한국어](README.md) | [English](README.en.md)*

# Anima / SongRyeon (송련)

> **A learning persona AI agent that thinks.**
> The field loop (day) operates the persona every turn; the midnight government (night) evolves the persona every day.
> A *plan-execute-critique* trio recurses at every layer.

[![Tests](https://img.shields.io/badge/tests-294%20passing-brightgreen)]() [![V4 §1-A](https://img.shields.io/badge/V4%20%C2%A71--A-LIVE-blue)]() [![Phase](https://img.shields.io/badge/Phase-1-blueviolet)]() [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) [![Python](https://img.shields.io/badge/python-3.10-blue)]()

---

## 1. Project Overview

**Anima** is not just an LLM response generator — it aims to be a *learning persona*. It performs reasoning at every user turn and refines/evolves itself every night, as a graph-neural-network persona.

Core vision (V4 §0):
> **SongRyeon is a persona that thinks and learns. The field loop (day) operates the persona every turn; the midnight government (night) evolves the persona every day. A plan-execute-critique trio recurses at every layer.**

Core principles (inherited from V3):
1. **Thinking belongs to -1s, planning to -1a, verification to 2b, speech to phase_3, review to -1b**
2. **Code handles tracking / safety / schema / execution / routing only. Meaning belongs entirely to the LLM**
3. **No self-evaluation** — work is never evaluated by its author
4. **Node ≠ LLM loop** — nodes are the skeleton, files are the flesh, the LLM is the thinking

---

## 2. Architecture Overview

### 2-1. Two time axes (day ↔ night)

```
   [Field loop = Day]                  [Midnight government = Night]
   Operates per user turn              Self-evolves every day
        ↓                                   ↓
   -1s → -1a → 2b → phase_3              recall → present → past → future
   (think → goal → fact → speak)         (4 departments + semantic-axis fork)
        ↓                                   ↓
        -1b review (comparator)             DreamHint generation →
         ↓                                  field loop advisory propagation
       phase_119 (sos)                      (time-axis / semantic-axis dual)
```

### 2-2. Field loop nodes (V4 §1-A LIVE)

| Node | Role | V4 definition |
|---|---|---|
| **-1s** (start_gate) | Cycle entry | **Situation judge** (user-intent normalization + thought-flow tracking + routing) |
| **-1a** (strategist) | Mid-cycle | **Goal-setter** (operational goal + execution plan; routing X) |
| **2b** (analyzer) | Fact judge | **Fact judge + thought critic** (auto-switch: fact mode / thought_critic mode) |
| **phase_3** (speaker) | Speaker | Answer text citing only verified facts |
| **-1b** (delivery_review) | Post review | Comparator (approve / remand / sos_119; tool calls X) |
| **0_supervisor** | Tool decision | Promoted to general-flow LLM after F4 (tool selection only) |
| **WarRoom** | sos-tier deep deliberation | Not used in normal operation |
| **phase_119** | Emergency response | Clean-failure response when all attempts fail |

### 2-3. Midnight government — 4 departments + semantic-axis fork

- **Recall department** (recent + random recall) — shared across time/semantic axes
- **Present department** (summarizer + problem raiser + fact checker)
- **Past department** (CoreEgo assembly — designer + self + approver)
- **Future department** (V3 trio instantiation — witness + critic + decision-maker)
- **Semantic government** (time-axis fork) — `python -m Core.midnight.semantic`

---

## 3. Tech Stack

- **Python 3.10**
- **LangGraph** (StateGraph-based node routing)
- **LangChain** (LLM adapters, prompt builders)
- **Neo4j** (persona graph store)
- **Ollama** (local LLM — gemma4 e4b + Llama 3.1, 4K context)
- **Pydantic** (schema enforcement — ThinkingHandoff.v1 / DeliveryReview.v1, etc.)
- **pytest** (294 tests passing)

---

## 4. Directory Layout

```
SongRyeon_Project/
├── Core/                       # Source code
│   ├── graph.py                # LangGraph wiring
│   ├── nodes.py                # Node implementations
│   ├── pipeline/               # -1s/-1a/2b/-1b pipelines + schemas
│   ├── prompt_builders.py      # LLM system prompts
│   ├── runtime/                # Context packet, working memory
│   ├── memory/                 # Memory adapters
│   ├── adapters/               # Neo4j, night queries
│   ├── midnight/               # Midnight government — 4 departments + semantic
│   │   ├── recall/             # Recall department
│   │   ├── present/            # Present department
│   │   ├── past/               # Past department
│   │   ├── future/             # Future department
│   │   └── semantic/           # Semantic-axis government
│   └── warroom/                # WarRoom package
├── tests/                      # Tests (294 OK, gitignored)
├── Orders/                     # Work orders / decision sheets (Phase 0/1)
├── ANIMA_FIELD_LOOP_V4_CONSTITUTION.md   # V4 constitution (LIVE LAW)
├── ANIMA_ARCHITECTURE_MAP.md             # Architecture map + purge log
├── ANIMA_DOCS_INDEX.md                   # Document navigation
├── AGENTS.md                             # AI collaborator working rules
├── main.py                               # Entry point
└── README.md                             # This file
```

---

## 5. Constitution System

Anima is developed under a **constitutional system**. At each evolution stage, the constitution is drafted, ratified, and enforced through a separation of powers: *legislature (Junghoo) → judicial advisory (Claude) → executive implementation (Codex)*.

| Constitution | Status | Ratified |
|---|---|---|
| V2 | SUPERSEDED | (legacy vision) |
| V3 | LIVE LAW (outside §1-A scope) | 2026-05-01 |
| **V4 §0 v0** | LIVE LAW | 2026-05-02 |
| **V4 §1-A** (Field-loop authority table) | **LIVE LAW** ★ | 2026-05-09 |
| **V4 §2** (Absolute prohibitions) | **LIVE LAW** ★ | 2026-05-09 |
| V4 §1-B (Midnight-government authority table) | Pending | After Phase 1 T-track review |
| V4 §1-C (Trio recursion + WarRoom v2) | Pending | After CR1 dispatch |

---

## 6. Development Phases

### Phase 0 — Cleanup (complete)
- Decomposed V3 god-file (`Core/midnight_reflection.py`, 5,330 lines) into 4-department packages (R1~R8, 8 stages)
- Slimmed `Core/nodes.py` (removed dead code such as `_fallback_strategist_output`)
- F1~F4 dispatches realigned field-loop authority from V3 → V4
- **Phase 0 → 1 entry gate satisfied** (midnight modules ≥3 ✓ / nodes heuristics ≤2 ✓ / 294 tests OK ✓ / V4 §1-A LIVE ✓)

### Phase 1 — Infrastructure (in progress)
- **CR1** (priority 1) — 2b thought-critic mode + -1s thought recursion + deterministic gate
- **T1** — DreamHint weighting + past-government integration (stepping stone toward Phase 2 activation propagation)
- **B9/B10** — 119 enum classification + modular response
- **C0.8/0.9/0.10** — Legacy fallback cleanup

### Phase 2 — Learning (planned)
- Activation-propagation prototype
- EpisodeCluster + EpisodeDream
- Night Fact Auditor + Governor Auditor
- Time-axis 3-split LLM loop

### Phase 3 — Integration (planned)
- CoreEgo dual aspect (graph node ↔ midnight avatar)
- Future node = tool strategy + past wiki + CoreEgo composite
- Bidirectional time + meta-thought department

---

## 7. Roles (Separation of Powers)

| Role | Owner |
|---|---|
| Vision decisions / constitution amendment | Junghoo (legislature) |
| Vision discussion + code diagnosis + Codex review | Claude (judicial advisory) |
| Code authoring/modification/testing | Codex (executive implementation) |
| Final approval (merge) | Junghoo |

V4 addition: **Divided collaboration mode** — drunk Junghoo (vision broadcasting) ↔ sober Junghoo (review) ↔ Claude (code-coordinate auto-attachment) ↔ Codex (implementation).

---

## 8. Getting Started

### 8-1. Environment setup

```powershell
# Install dependencies
py -3.10 -m pip install -r requirements.txt   # (requirements.txt is a Junghoo-environment dependency reference)

# .env environment variables (gitignored)
# NEO4J_URI=bolt://localhost:7687
# NEO4J_USER=neo4j
# NEO4J_PASSWORD=<your_password>
# OLLAMA_BASE_URL=http://localhost:11434
# ANTHROPIC_API_KEY=<optional, for Claude>
```

### 8-2. Run

```powershell
# Field loop (user turn)
py -3.10 main.py

# Midnight government (time axis)
py -3.10 -m Core.midnight

# Midnight government (semantic-axis fork included)
py -3.10 -m Core.midnight.semantic
```

### 8-3. Tests

```powershell
py -3.10 -m pytest
# 294 tests passed
```

> **Note**: The `tests/` folder is gitignored (per Junghoo's decision on 2026-05-09). Test code is for local development + Codex verification.

---

## 9. Documentation

Core documents are provided in both Korean and English:

| Document | 한국어 | English |
|---|---|---|
| Project README | [README.md](README.md) | [README.en.md](README.en.md) |
| AI collaborator working rules | [AGENTS.md](AGENTS.md) | [AGENTS.en.md](AGENTS.en.md) |
| Document navigation | [ANIMA_DOCS_INDEX.md](ANIMA_DOCS_INDEX.md) | [ANIMA_DOCS_INDEX.en.md](ANIMA_DOCS_INDEX.en.md) |
| V4 constitution | [ANIMA_FIELD_LOOP_V4_CONSTITUTION.md](ANIMA_FIELD_LOOP_V4_CONSTITUTION.md) | [ANIMA_FIELD_LOOP_V4_CONSTITUTION.en.md](ANIMA_FIELD_LOOP_V4_CONSTITUTION.en.md) |
| V3 constitution | [ANIMA_FIELD_LOOP_V3_CONSTITUTION.md](ANIMA_FIELD_LOOP_V3_CONSTITUTION.md) | [ANIMA_FIELD_LOOP_V3_CONSTITUTION.en.md](ANIMA_FIELD_LOOP_V3_CONSTITUTION.en.md) |
| Architecture map | [ANIMA_ARCHITECTURE_MAP.md](ANIMA_ARCHITECTURE_MAP.md) | [ANIMA_ARCHITECTURE_MAP.en.md](ANIMA_ARCHITECTURE_MAP.en.md) |
| Reform V1 vision | [ANIMA_REFORM_V1.md](ANIMA_REFORM_V1.md) | [ANIMA_REFORM_V1.en.md](ANIMA_REFORM_V1.en.md) |
| Reform V1 implementation | [ANIMA_REFORM_IMPLEMENTATION_V1.md](ANIMA_REFORM_IMPLEMENTATION_V1.md) | [ANIMA_REFORM_IMPLEMENTATION_V1.en.md](ANIMA_REFORM_IMPLEMENTATION_V1.en.md) |
| State optimization checklist | [ANIMA_State_Optimization_Checklist.md](ANIMA_State_Optimization_Checklist.md) | [ANIMA_State_Optimization_Checklist.en.md](ANIMA_State_Optimization_Checklist.en.md) |

> Other Korean-only documents (V4 vision drafts, Sleep Stack, Orders/ work orders) are Junghoo's single-user work materials and are not translated to English.

---

## 10. License

[MIT License](LICENSE) — anyone may freely use, modify, and redistribute. The copyright notice and license text must be preserved.

This project started as Junghoo (Junghoo-developer)'s personal research. External contributions and discussion are welcome.

---

**Version**: V4 §1-A LIVE (2026-05-09) | **Phase**: 1 (CR1 stand-by) | **Tests**: 294 OK
