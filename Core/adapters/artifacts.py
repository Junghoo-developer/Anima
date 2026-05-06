"""Local artifact lookup and text extraction for ANIMA tools."""

import html
import os
import re
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ONEDRIVE_ROOT = PROJECT_ROOT.parent.parent
ARTIFACT_EXTENSIONS = {".pptx", ".txt", ".md", ".json", ".py", ".docx"}


def _normalize_artifact_key(text) -> str:
    return re.sub(r"[\s_\-./\\]+", "", str(text or "").strip()).lower()


def _candidate_roots(search_roots=None):
    if search_roots is None:
        return [(PROJECT_ROOT, True), (ONEDRIVE_ROOT, False)]
    return [(Path(root), True) for root in search_roots]


def _iter_artifact_candidates(search_roots=None):
    seen = set()
    for root, recursive in _candidate_roots(search_roots):
        if not root.exists():
            continue
        if root.is_file():
            candidates = [root]
        elif recursive:
            try:
                candidates = (path for path in root.rglob("*") if path.is_file())
            except OSError:
                continue
        else:
            try:
                candidates = (path for path in root.iterdir() if path.is_file())
            except OSError:
                continue
        for path in candidates:
            ext = path.suffix.lower()
            if ext not in ARTIFACT_EXTENSIONS:
                continue
            resolved = str(path.resolve())
            if resolved in seen:
                continue
            seen.add(resolved)
            yield path


def _find_artifact_path(artifact_hint, *, search_roots=None) -> str:
    hint = str(artifact_hint or "").strip().strip('"').strip("'")
    if not hint:
        return ""

    direct_path = Path(hint)
    if direct_path.is_file():
        return str(direct_path.resolve())

    hint_key = _normalize_artifact_key(Path(hint).name)
    hint_tokens = [token for token in re.split(r"\s+", hint.lower()) if token]
    best_score = -1
    best_path = ""

    for candidate in _iter_artifact_candidates(search_roots=search_roots):
        base = candidate.name
        stem = candidate.stem
        candidate_key = _normalize_artifact_key(base)
        stem_key = _normalize_artifact_key(stem)

        score = 0
        if hint_key and hint_key == candidate_key:
            score += 100
        if hint_key and hint_key == stem_key:
            score += 95
        if hint_key and hint_key in candidate_key:
            score += 70
        if hint_key and hint_key in stem_key:
            score += 65
        if hint_tokens:
            token_hits = sum(1 for token in hint_tokens if token and token in base.lower())
            score += token_hits * 10
        if "ANIMA" in base.upper():
            score += 2

        if score > best_score:
            best_score = score
            best_path = str(candidate.resolve())

    return best_path if best_score > 0 else ""


def _read_text_like_artifact(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def _read_pptx_artifact(path: str) -> str:
    slides = []
    with zipfile.ZipFile(path) as zf:
        slide_names = [
            name
            for name in zf.namelist()
            if name.startswith("ppt/slides/slide") and name.endswith(".xml")
        ]
        slide_names.sort(key=lambda name: int(re.search(r"slide(\d+)\.xml$", name).group(1)))

        for idx, name in enumerate(slide_names[:20], start=1):
            xml_text = zf.read(name).decode("utf-8", errors="ignore")
            texts = [html.unescape(t).strip() for t in re.findall(r"<a:t>(.*?)</a:t>", xml_text, re.DOTALL)]
            texts = [t for t in texts if t]
            if texts:
                slides.append(f"[slide {idx}] " + " ".join(texts))

    return "\n".join(slides)


def _read_docx_artifact(path: str) -> str:
    with zipfile.ZipFile(path) as zf:
        xml_text = zf.read("word/document.xml").decode("utf-8", errors="ignore")
    texts = [html.unescape(t).strip() for t in re.findall(r"<w:t[^>]*>(.*?)</w:t>", xml_text, re.DOTALL)]
    texts = [t for t in texts if t]
    return "\n".join(texts)


def read_artifact(
    artifact_hint,
    *,
    search_roots=None,
    max_chars: int = 12000,
) -> tuple[str, list[str]]:
    """Resolve and read a local artifact by path or fuzzy filename."""
    hint = str(artifact_hint or "").strip()
    if not hint:
        return "[artifact error] Empty artifact hint.", []

    path = _find_artifact_path(hint, search_roots=search_roots)
    if not path:
        return f"[artifact not found] Could not resolve '{hint}'.", []

    ext = os.path.splitext(path)[1].lower()
    try:
        if ext in {".txt", ".md", ".json", ".py"}:
            body = _read_text_like_artifact(path)
        elif ext == ".pptx":
            body = _read_pptx_artifact(path)
        elif ext == ".docx":
            body = _read_docx_artifact(path)
        else:
            return f"[artifact unsupported] {ext} is not supported yet for '{path}'.", [path]
    except Exception as exc:
        return f"[artifact read error] Failed to read '{path}': {exc}", [path]

    body = body.strip() or "(No readable text extracted.)"
    header = (
        f"[artifact]\n"
        f"path: {path}\n"
        f"type: {ext or 'unknown'}\n"
        f"name: {os.path.basename(path)}\n\n"
    )
    return header + body[:max_chars], [path]


__all__ = ["ARTIFACT_EXTENSIONS", "ONEDRIVE_ROOT", "PROJECT_ROOT", "read_artifact"]
