import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOTS = [PROJECT_ROOT / "Core", PROJECT_ROOT / "tests", PROJECT_ROOT / "tools"]
ROOT_SOURCE_FILES = [PROJECT_ROOT / "main.py", PROJECT_ROOT / "migrate_to_neo4j.py"]

MOJIBAKE_MARKERS = tuple(
    chr(codepoint)
    for codepoint in [
        0xFFFD,
        0x00C2,
        0x00C3,
        0x00EC,
        0x00ED,
        0x00EA,
        0x00EB,
        0xF9DE,
        0xF9B2,
        0x6D39,
        0x7B4C,
        0x91AB,
        0x7344,
        0x7650,
        0x63F6,
    ]
)


def _source_files():
    for root in SOURCE_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if "__pycache__" not in path.parts:
                yield path
    for path in ROOT_SOURCE_FILES:
        if path.exists():
            yield path


class EncodingGuardTests(unittest.TestCase):
    def test_python_sources_are_utf8_without_bom(self):
        offenders = []
        for path in _source_files():
            data = path.read_bytes()
            if data.startswith(b"\xef\xbb\xbf"):
                offenders.append(f"{path.relative_to(PROJECT_ROOT)}: UTF-8 BOM")
                continue
            try:
                data.decode("utf-8", errors="strict")
            except UnicodeDecodeError as exc:
                offenders.append(f"{path.relative_to(PROJECT_ROOT)}: invalid UTF-8 at byte {exc.start}")

        self.assertEqual([], offenders)

    def test_python_sources_do_not_contain_known_mojibake_markers(self):
        offenders = []
        for path in _source_files():
            text = path.read_text(encoding="utf-8")
            found = sorted({marker for marker in MOJIBAKE_MARKERS if marker in text})
            if found:
                escaped = ", ".join(f"U+{ord(marker):04X}" for marker in found)
                offenders.append(f"{path.relative_to(PROJECT_ROOT)}: {escaped}")

        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
