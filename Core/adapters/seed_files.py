"""SEED file read/write helpers for legacy tool compatibility."""

import json
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INSTINCTS_DIR = PROJECT_ROOT / "SEED" / "Instincts"
PROMPTS_DIR = PROJECT_ROOT / "SEED" / "prompts"
PROMPT_FILE_MAP = {
    "0": "0_meta_prompt.txt",
    "2": "2_analyzer_prompt.txt",
    "3": "3_validator_prompt.txt",
}


def update_instinct_file(filename, rule_index, new_voice) -> str:
    """Update one rule voice in a SEED/Instincts JSON file."""
    safe_name = os.path.basename(str(filename or "").strip())
    if not safe_name:
        return "[seed file error] Empty instinct filename."
    target_path = INSTINCTS_DIR / safe_name
    if not target_path.exists():
        return f"[seed file error] File not found: {safe_name}"

    try:
        index = int(rule_index)
    except Exception:
        return f"[seed file error] rule_index must be an integer: {rule_index!r}"

    try:
        data = json.loads(target_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return f"[seed file error] Failed to read {safe_name}: {exc}"

    rules = data.get("rules")
    if not isinstance(rules, list):
        return f"[seed file error] {safe_name} has no rules list."
    if not 0 <= index < len(rules):
        return f"[seed file error] rule_index out of range: 0..{len(rules) - 1}"

    old_voice = rules[index].get("voice", "")
    rules[index]["voice"] = str(new_voice or "").strip()
    try:
        target_path.write_text(json.dumps(data, ensure_ascii=False, indent=4), encoding="utf-8")
    except Exception as exc:
        return f"[seed file error] Failed to write {safe_name}: {exc}"

    return f"[seed file updated] {safe_name} rule {index}: {old_voice!r} -> {rules[index]['voice']!r}"


def _normalize_prompt_phase(target_phase) -> str:
    text = str(target_phase or "").strip()
    text = text.replace("phase_", "").replace("Phase_", "").replace("차", "").strip()
    return text


def update_core_prompt(target_prompt, new_full_text) -> str:
    """Replace a core prompt file by phase id."""
    phase = _normalize_prompt_phase(target_prompt)
    filename = PROMPT_FILE_MAP.get(phase)
    if not filename:
        return f"[prompt file error] Unsupported phase: {target_prompt}"
    body = str(new_full_text or "").strip()
    if not body or body.upper() == "NONE":
        return "[prompt file error] New prompt text is empty."
    target_path = PROMPTS_DIR / filename
    try:
        target_path.write_text(body, encoding="utf-8")
    except Exception as exc:
        return f"[prompt file error] Failed to write {filename}: {exc}"
    return f"[prompt file updated] {filename}"


def read_prompt_file(target_phase) -> str:
    """Read a core prompt file by phase id."""
    phase = _normalize_prompt_phase(target_phase)
    filename = PROMPT_FILE_MAP.get(phase)
    if not filename:
        return f"[prompt file error] Unsupported phase: {target_phase}"
    target_path = PROMPTS_DIR / filename
    try:
        body = target_path.read_text(encoding="utf-8")
    except Exception as exc:
        return f"[prompt file error] Failed to read {filename}: {exc}"
    return f"[prompt file: {filename}]\n{body}"


__all__ = [
    "INSTINCTS_DIR",
    "PROJECT_ROOT",
    "PROMPTS_DIR",
    "read_prompt_file",
    "update_core_prompt",
    "update_instinct_file",
]
