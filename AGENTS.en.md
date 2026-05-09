*[한국어](AGENTS.md) | [English](AGENTS.en.md)*

# AGENTS.md — Working Rules for Codex / AI Collaborators

These are the operating rules that Codex and any other AI collaborator must follow in this repository.
While the constitution (`ANIMA_FIELD_LOOP_V3_CONSTITUTION.md`) defines *what* is built,
this document defines *how* it is handled.

---

## 1. Encoding Rules (Korean / UTF-8 documents)

Every `.md`, `.py`, `.json`, `.yml`, `.txt` file in this repository is **UTF-8 (no BOM)**.
The default encoding for Windows PowerShell's `Get-Content` / `Set-Content` is not UTF-8,
so Korean characters may appear as mojibake. **This is a reader-side configuration issue, not a corrupted file.**

### 1.1 Reading files in PowerShell
```powershell
# OK
Get-Content path\to\file.md -Encoding UTF8
Get-Content path\to\file.md -Raw -Encoding UTF8

# Forbidden (causes mojibake)
Get-Content path\to\file.md
cat path\to\file.md
```

### 1.2 Writing files in PowerShell
```powershell
# OK (UTF-8 without BOM)
$content | Out-File -FilePath path\to\file.md -Encoding utf8 -NoNewline
$content | Set-Content -Path path\to\file.md -Encoding utf8

# Forbidden (becomes UTF-16 LE or UTF-8 with BOM)
$content > path\to\file.md
$content | Out-File path\to\file.md
```

### 1.3 Reading and writing files in Python
```python
# OK
with open(path, "r", encoding="utf-8") as f: ...
with open(path, "w", encoding="utf-8") as f: ...

# Forbidden (Windows opens with cp949 → UnicodeDecodeError or mojibake)
with open(path) as f: ...
```

### 1.4 Diagnostic procedure

If a document appears broken, **before rewriting**, always check the following first:

1. Verify the actual encoding via `file path/to/file.md` (Git Bash) or another tool.
2. In PowerShell, re-read with `Get-Content -Encoding UTF8`.
3. Only consider rewriting if the file is still broken.

**Document rewriting is the last resort.** Skipping the encoding diagnosis and deciding "since Korean is broken, let's rewrite in ASCII" is forbidden.

---

## 2. Division of Labor (Human ↔ AI, identical to Constitution §11)

| Role | Owner |
|------|------|
| Vision decisions / constitution amendment | Junghoo (legislature) |
| Vision discussion + code diagnosis + Codex work review | Claude (judicial advisory) |
| Code authoring/modification/testing | Codex (executive implementation) |
| Final approval (merge) | Junghoo |

Codex does not interfere with vision decisions. If a constitutional interpretation is unclear, Codex stops work and consults Junghoo / Claude.

---

## 3. Single Source of Truth

All work is governed by the following priority order:

0. `ANIMA_DOCS_INDEX.md` — Document navigation (which document to read when)
1. `ANIMA_FIELD_LOOP_V3_CONSTITUTION.md` — Constitution (authority table, absolute prohibitions, ratified by Junghoo on 2026-05-01)
2. `ANIMA_ARCHITECTURE_MAP.md` — Current structure map and purge log
3. `ANIMA_State_Optimization_Checklist.md` — Token-normalization checklist
4. `ANIMA_REFORM_V1.md`, `ANIMA_REFORM_IMPLEMENTATION_V1.md` — Background / absorbed vision documents
5. `ANIMA_WARROOM_V2_SCHEMA.md`, `ANIMA_SLEEP_STACK_V1.md`, `ANIMA_SLEEP_STACK_V2.md` — Future design documents
6. This document (`AGENTS.md`) — Operating rules

When existing code conflicts with the documents above, **the document wins.** Code is aligned to the constitution.

### 3.1 Default reading set before any surgery

Before Codex modifies field-loop code, only the following four documents must be read by default:

1. `AGENTS.md`
2. `ANIMA_DOCS_INDEX.md`
3. `ANIMA_FIELD_LOOP_V3_CONSTITUTION.md`
4. `ANIMA_ARCHITECTURE_MAP.md`

For token/state optimization work, additionally read `ANIMA_State_Optimization_Checklist.md`.
Unless the work is WarRoom- or midnight-government-related, do not treat `ANIMA_WARROOM_V2_SCHEMA.md`,
`ANIMA_SLEEP_STACK_V1.md`, or `ANIMA_SLEEP_STACK_V2.md` as direct coding references.

### 3.2 Document status rules

- `LIVE LAW`: The legal basis for current code changes.
- `LIVE STATUS`: Current implementation state and work log.
- `BACKGROUND / ABSORBED`: Philosophy and history. If they conflict with the current constitution, the constitution wins.
- `FUTURE DESIGN`: Next-pass proposals. They do not automatically override the current constitution.

When a new design document is added, register its status in `ANIMA_DOCS_INDEX.md` first, then use it.

### 3.2.1 Codex memory-access rule

Even if Claude or Junghoo references a design document under `memory/...` or "in my memory",
Codex must not assume that the path can be read directly from the current filesystem.

- First verify actual file existence via `rg --files` or explicit path checks.
- If the file does not exist, **report that it is missing** and base work only on the work order pasted in messages by the user/Claude or on LIVE documents in the repository.
- Do not implement or override the constitution / ARCH MAP based on guessed memory contents.
- To use a memory document as a coding reference, first add it to the repository as a file and register its status in `ANIMA_DOCS_INDEX.md`.

### 3.3 Constitutional review before large `nodes.py` surgery

Before starting any large inventory, deletion, or relocation operation in `Core/nodes.py`,
Junghoo must first approve the following items in `ANIMA_FIELD_LOOP_V3_CONSTITUTION.md`:

1. §0 one-line summary
2. §1 core 5-node authority table (`-1s`, `-1a`, `-1b`, `2b`, `phase_3`)
3. §2 fifteen absolute prohibitions

Without prior approval, do not bulk-classify the 6,000-line code based on documents.

---

**Version**: V1 draft (2026-05-01)
**Update trigger**: Whenever Codex repeats the same mistake twice, append the item to this document.
