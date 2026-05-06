# V3 Midnight Government Archive

Archived by order `#R1` on 2026-05-05.

## Why This Exists

The old V3 midnight-government loop was archived after the V4 meaning-axis
government direction made the old 11-phase decomposition obsolete. This is the
approved path: remove the old live system first, preserve the reusable ideas,
then rebuild the future departments from the new V4 vision.

This archive is intentionally not a live import surface. Files here are kept for
reference and future revival only.

## Revival Candidates

These three files are explicitly preserved as meaning-axis revival candidates:

| Candidate | Archived path | Intended revival point |
|---|---|---|
| REMGovernor | `rem_governor.py` | When the meaning-axis government is implemented in earnest |
| StrategyCouncil | `midnight/strategy_council.py` | When the meaning-axis government is implemented in earnest |
| BranchArchitect | `branch_architect.py` | When the meaning-axis government is implemented in earnest |

## Archived Files

| File | MD5 before move | Bytes |
|---|---:|---:|
| `midnight_reflection.py` | `4A7A052271F2CA3294D6257EC6F50965` | 139595 |
| `rem_governor.py` | `D7A9E0FE83CD944C55CE48A02CE44274` | 17586 |
| `branch_architect.py` | `FE5CC9E93FB3FACC0D0AE422C0A1D3BE` | 20824 |
| `midnight/strategy_council.py` | `1728E411F8C03ACE8552B5E8FC280AC7` | 47362 |
| `midnight/rem_plan.py` | `5938520A906BB0CA44D7ED7C7AB32DA9` | 10776 |
| `midnight/rem_governor.py` | `D221F08A2CEEEA147A71C31471C63F84` | 45575 |
| `midnight/policy_doctrine.py` | `352A4AE4345AED65C2E17F8B5EBA5987` | 32849 |
| `midnight/__init__.py` | `9D321BC9DBA0F5CD8F2C083CA2FE8277` | 47 |
| `midnight_reflection_contracts.py` | `DDA9ABBCD3C5F741465B84D64A9D1E66` | 12409 |
| `night_branch_growth_persistence.py` | `BF940CC4898E1FBB8F2892D47C48A736` | 46984 |
| `night_government_persistence.py` | `EAE28ED59893F422B3CD8C28EDC5B468` | 23095 |
| `night_strategy_persistence.py` | `795804D580DAD93B1F41890987744426` | 13499 |
| `night_policy_persistence.py` | `7FAAD7F24FBE3948EC43E12DC2EB1F92` | 8644 |
| `night_tactical_persistence.py` | `07929F436DE030BAA5643D74FE1A88E0` | 8509 |
| `night_persistence_utils.py` | `950F108586CBA49C8318D445B34A92F1` | 1908 |

`night_persistence_utils.py`, `midnight/rem_governor.py`,
`midnight/policy_doctrine.py`, and `midnight/__init__.py` were included because
dependency tracing showed they belonged to the old midnight-government island.

## Live Caller Table For #R2

After the archive move, direct live imports of the archived modules were gone.
The remaining references are not runtime imports, but they mark the next cleanup
surface:

| Caller | Reference | #R2 action |
|---|---|---|
| `Core/field_memo.py` | `rem_governor_v1`, `GovernorBranch`, `REMGovernorState`, `apply_local_reports_to_governor` | Decide whether these old governor labels/helpers are archived, renamed, or rebuilt under the new memory/meaning-axis government. |
| `tools/__init__.py` | Comment mentioning `python Core/midnight_reflection.py` | Update the developer-tool note so it no longer points at the archived entrypoint. |
| Planning docs / orders | Historical mentions of old midnight files | Leave as history unless a live-status document claims these files still exist. |

## Archive Rule

Do not import from this folder in live runtime code. Revival should happen by
copying the selected concept into a new V4 module with a fresh contract.
