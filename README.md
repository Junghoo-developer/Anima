*[한국어](README.md) | [English](README.en.md)*

# Anima / 송련 (SongRyeon)

> **사고하며 학습하는 인격 AI 에이전트.**
> 현장 루프(낮)가 매 턴 인격을 작동시키고, 심야 정부(밤)가 매일 인격을 진화시킨다.
> 어느 층에서나 *계획-실행-비판* 트리오가 재귀한다.

[![Tests](https://img.shields.io/badge/tests-294%20passing-brightgreen)]() [![V4 §1-A](https://img.shields.io/badge/V4%20%C2%A71--A-LIVE-blue)]() [![Phase](https://img.shields.io/badge/Phase-1-blueviolet)]() [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) [![Python](https://img.shields.io/badge/python-3.10-blue)]()

---

## 1. 프로젝트 개요

**Anima**는 단순 LLM 응답 생성기가 아니라 *학습하는 인격*을 목표로 한다. 매 사용자 턴마다 사고를 수행하고, 밤마다 자기 자신을 정제·진화시키는 그래프 신경망 인격이다.

코어 비전 (V4 §0):
> **송련은 사고하며 학습하는 인격이다. 현장 루프(낮)가 매 턴 인격을 작동시키고, 심야 정부(밤)가 매일 인격을 진화시킨다. 어느 층에서나 계획-실행-비판 트리오가 재귀한다.**

핵심 원칙 (V3에서 계승):
1. **사고는 -1s, 수립은 -1a, 검증은 2b, 발화는 phase_3, 결재는 -1b**
2. **코드는 추적·안전·schema·실행·라우팅만. 의미는 모두 LLM**
3. **자기 평가 금지** — 자기 작업은 자기가 평가하지 않는다
4. **노드 ≠ LLM 루프** — 노드는 뼈대, 파일은 살, LLM은 사고

---

## 2. 아키텍처 개관

### 2-1. 두 시간축 (낮 ↔ 밤)

```
   [현장 루프 = 낮]                    [심야 정부 = 밤]
   매 사용자 턴 작동                   매일 자기 진화
        ↓                                 ↓
   -1s → -1a → 2b → phase_3              회상 → 현재 → 과거 → 미래
   (사고 → 목표 → 사실 → 발화)          (4부서 + 의미축 fork)
        ↓                                 ↓
        -1b 결재 (대조관)                  DreamHint 생성 →
         ↓                              현장 루프에 advisory 전파
       phase_119 (sos)                    (시간축/의미축 양면)
```

### 2-2. 현장 루프 노드 (V4 §1-A LIVE)

| 노드 | 본업 | V4 정의 |
|---|---|---|
| **-1s** (start_gate) | 사이클 시작점 | **상황 판단자** (사용자 의도 정제 + 사고 흐름 추적 + 라우팅) |
| **-1a** (strategist) | 사이클 중 | **목표 수립자** (작전 목표 + 실행계획. 라우팅 X) |
| **2b** (analyzer) | 사실 판사 | **사실 판사 + 사고 비판자** (fact mode + thought_critic mode 자동 전환) |
| **phase_3** (speaker) | 발화자 | 검증 사실만 인용한 답변 텍스트 |
| **-1b** (delivery_review) | 사후 결재 | 대조관 (approve/remand/sos_119, 도구 호출 X) |
| **0_supervisor** | 도구 결정 | F4 후 LLM 일반 흐름 격상 (도구 선택만) |
| **WarRoom** | sos급 깊은 토론 | 평시 사용 X |
| **phase_119** | 비상 답변 | 모든 시도 실패 시 깔끔한 실패 응답 |

### 2-3. 심야 정부 4부서 + 의미축 fork

- **회상 부서** (recent + random recall) — 시간축/의미축 공유
- **현재 부서** (정리자 + 문제제기자 + 사실검증자)
- **과거 부서** (CoreEgo 의회 — 설계자 + 자아 + 결재자)
- **미래 부서** (V3 트리오 instantiation — 목격자 + 비판자 + 결재자)
- **의미축 정부** (시간축 fork) — `python -m Core.midnight.semantic`

---

## 3. 기술 스택

- **Python 3.10**
- **LangGraph** (StateGraph 기반 노드 라우팅)
- **LangChain** (LLM 어댑터, prompt builders)
- **Neo4j** (인격 그래프 저장소)
- **Ollama** (로컬 LLM — gemma4 e4b + Llama 3.1, 4K 컨텍스트)
- **Pydantic** (schema 강제 — ThinkingHandoff.v1 / DeliveryReview.v1 등)
- **pytest** (294 tests passing)

---

## 4. 디렉토리 구조

```
SongRyeon_Project/
├── Core/                       # 본 코드
│   ├── graph.py                # LangGraph wiring
│   ├── nodes.py                # 노드 본체
│   ├── pipeline/               # -1s/-1a/2b/-1b 파이프라인 + schema
│   ├── prompt_builders.py      # LLM 시스템 프롬프트
│   ├── runtime/                # context packet, working memory
│   ├── memory/                 # 메모리 어댑터
│   ├── adapters/               # Neo4j, night queries
│   ├── midnight/               # 심야 정부 4부서 + 의미축
│   │   ├── recall/             # 회상 부서
│   │   ├── present/            # 현재 부서
│   │   ├── past/               # 과거 부서
│   │   ├── future/             # 미래 부서
│   │   └── semantic/           # 의미축 정부
│   └── warroom/                # WarRoom 패키지
├── tests/                      # 테스트 (294 OK, .gitignore)
├── Orders/                     # 발주서 / 결재 시트 (Phase 0/1)
├── ANIMA_FIELD_LOOP_V4_CONSTITUTION.md   # V4 헌법 (LIVE LAW)
├── ANIMA_ARCHITECTURE_MAP.md             # 아키텍처 지도 + purge log
├── ANIMA_DOCS_INDEX.md                   # 문서 네비게이션
├── AGENTS.md                             # AI 협업자 작업 규칙
├── main.py                               # 진입점
└── README.md                             # 본 파일
```

---

## 5. 헌법 (Constitution) 시스템

Anima 개발은 **헌법 기반**이다. 각 진화 단계마다 헌법이 *입법부 (정후) → 사법부 자문 (Claude) → 행정부 실무 (Codex)* 분업으로 작성·통과·시행된다.

| 헌법 | 상태 | 통과 일자 |
|---|---|---|
| V2 | SUPERSEDED | (옛 비전) |
| V3 | LIVE LAW (§1-A 외 영역) | 2026-05-01 |
| **V4 §0 v0** | LIVE LAW | 2026-05-02 |
| **V4 §1-A** (현장 루프 권한표) | **LIVE LAW** ★ | 2026-05-09 |
| **V4 §2** (절대 금지 목록) | **LIVE LAW** ★ | 2026-05-09 |
| V4 §1-B (심야 정부 권한표) | 작성 예정 | Phase 1 T트랙 검수 후 |
| V4 §1-C (트리오 재귀 + WarRoom v2) | 작성 예정 | CR1 발주 후 |

---

## 6. 개발 단계 (Phases)

### Phase 0 — 청소 (완료)
- V3 god-file (`Core/midnight_reflection.py` 5,330줄) 분해 → 4부서 패키지 (R1~R8 8단계)
- `Core/nodes.py` 다이어트 (`_fallback_strategist_output` 등 죽은 코드 제거)
- F1~F4 발주 = 현장 루프 V3 → V4 권한 재정렬
- **Phase 0 → 1 진입 게이트 충족** (midnight 모듈 ≥3 ✓ / nodes heuristic ≤2 ✓ / 294 tests OK ✓ / V4 §1-A LIVE ✓)

### Phase 1 — 인프라 (진행 중)
- **CR1** (1순위) — 2b 사고 비판자 (thought_critic mode) + -1s 사고 재귀 + deterministic 게이트
- **T1** — DreamHint 가중치 + 과거 정부 통합 (Phase 2 활성화 전파 디딤돌)
- **B9/B10** — 119 enum 분류 + 모듈식 답변
- **C0.8/0.9/0.10** — legacy fallback 정리

### Phase 2 — 학습 (예정)
- 활성화 전파 prototype
- EpisodeCluster + EpisodeDream
- Night Fact Auditor + Governor Auditor
- 시간축 3분할 LLM 루프

### Phase 3 — 통합 (예정)
- CoreEgo 양면 (그래프 노드 ↔ 심야 분신)
- 미래 노드 = 도구 전략 + 과거 wiki + CoreEgo 합성체
- 양방향 시간 + 메타 사고 부서

---

## 7. 분업 (역할)

| 역할 | 담당 |
|---|---|
| 비전 결정 / 헌법 개정 | 정후 (입법부) |
| 비전 토론 + 코드 진단 + Codex 작업 검수 | Claude (사법부 자문) |
| 코드 작성/수정/테스트 | Codex (행정부 실무) |
| 최종 결재 (merge) | 정후 |

V4에서 추가: **분업 모드** — 술 정후 (비전 발화) ↔ 깬 정후 (결재) ↔ Claude (코드 좌표 자동 동봉) ↔ Codex (실무).

---

## 8. 시작하기 (Getting Started)

### 8-1. 환경 설정

```powershell
# 의존성 설치
py -3.10 -m pip install -r requirements.txt   # (requirements.txt는 정후 환경 의존성 reference)

# .env 환경변수 (gitignore 처리됨)
# NEO4J_URI=bolt://localhost:7687
# NEO4J_USER=neo4j
# NEO4J_PASSWORD=<your_password>
# OLLAMA_BASE_URL=http://localhost:11434
# ANTHROPIC_API_KEY=<optional, for Claude>
```

### 8-2. 실행

```powershell
# 현장 루프 (사용자 턴)
py -3.10 main.py

# 심야 정부 (시간축)
py -3.10 -m Core.midnight

# 심야 정부 (의미축 fork 포함)
py -3.10 -m Core.midnight.semantic
```

### 8-3. 테스트

```powershell
py -3.10 -m pytest
# 294 tests passed
```

> **주의**: `tests/` 폴더는 `.gitignore` 처리됨 (정후 결재 2026-05-09). 테스트 코드는 local 작업 + Codex 검증용.

---

## 9. 문서 (Documentation)

핵심 문서는 모두 한국어/영문 두 벌로 제공:

| 문서 | 한국어 | English |
|---|---|---|
| 프로젝트 README | [README.md](README.md) | [README.en.md](README.en.md) |
| AI 협업자 작업 규칙 | [AGENTS.md](AGENTS.md) | [AGENTS.en.md](AGENTS.en.md) |
| 문서 네비게이션 | [ANIMA_DOCS_INDEX.md](ANIMA_DOCS_INDEX.md) | [ANIMA_DOCS_INDEX.en.md](ANIMA_DOCS_INDEX.en.md) |
| V4 헌법 | [ANIMA_FIELD_LOOP_V4_CONSTITUTION.md](ANIMA_FIELD_LOOP_V4_CONSTITUTION.md) | [ANIMA_FIELD_LOOP_V4_CONSTITUTION.en.md](ANIMA_FIELD_LOOP_V4_CONSTITUTION.en.md) |
| V3 헌법 | [ANIMA_FIELD_LOOP_V3_CONSTITUTION.md](ANIMA_FIELD_LOOP_V3_CONSTITUTION.md) | [ANIMA_FIELD_LOOP_V3_CONSTITUTION.en.md](ANIMA_FIELD_LOOP_V3_CONSTITUTION.en.md) |
| 아키텍처 지도 | [ANIMA_ARCHITECTURE_MAP.md](ANIMA_ARCHITECTURE_MAP.md) | [ANIMA_ARCHITECTURE_MAP.en.md](ANIMA_ARCHITECTURE_MAP.en.md) |
| Reform V1 비전 | [ANIMA_REFORM_V1.md](ANIMA_REFORM_V1.md) | [ANIMA_REFORM_V1.en.md](ANIMA_REFORM_V1.en.md) |
| Reform V1 시행 | [ANIMA_REFORM_IMPLEMENTATION_V1.md](ANIMA_REFORM_IMPLEMENTATION_V1.md) | [ANIMA_REFORM_IMPLEMENTATION_V1.en.md](ANIMA_REFORM_IMPLEMENTATION_V1.en.md) |
| State 최적화 체크리스트 | [ANIMA_State_Optimization_Checklist.md](ANIMA_State_Optimization_Checklist.md) | [ANIMA_State_Optimization_Checklist.en.md](ANIMA_State_Optimization_Checklist.en.md) |

> 다른 한국어 전용 문서 (V4 비전, Sleep Stack, Orders/ 발주서 등)는 정후 single-user 작업 자료로 영문 미번역.

---

## 10. 라이선스 (License)

[MIT License](LICENSE) — 누구나 자유롭게 사용/수정/재배포 가능. 단 저작권 표기 + 라이선스 사본 보존 의무.

본 프로젝트는 정후 (Junghoo-developer) 개인 연구 프로젝트로 시작. 외부 기여/논의 환영.

---

**버전**: V4 §1-A LIVE (2026-05-09) | **Phase**: 1 (CR1 stand-by) | **Tests**: 294 OK
