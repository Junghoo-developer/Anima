import tempfile
import unittest
from pathlib import Path

from Core.adapters import artifacts
from Core.tools import tool_read_artifact
from tools import toolbox


class ArtifactAdapterTests(unittest.TestCase):
    def test_read_artifact_reads_exact_text_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "notes.txt"
            path.write_text("hello artifact", encoding="utf-8")

            text, ids = artifacts.read_artifact(str(path))

        self.assertEqual(len(ids), 1)
        self.assertIn("[artifact]", text)
        self.assertIn("notes.txt", text)
        self.assertIn("hello artifact", text)

    def test_read_artifact_can_fuzzy_match_with_search_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "ANIMA memory map.md"
            path.write_text("memory map body", encoding="utf-8")

            text, ids = artifacts.read_artifact("memory map", search_roots=[root])

        self.assertEqual(len(ids), 1)
        self.assertIn("ANIMA memory map.md", text)
        self.assertIn("memory map body", text)

    def test_toolbox_read_artifact_delegates_to_adapter(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "delegated.md"
            path.write_text("delegated body", encoding="utf-8")

            text, ids = toolbox.read_artifact(str(path))

        self.assertEqual(len(ids), 1)
        self.assertIn("delegated body", text)

    def test_live_tool_read_artifact_uses_adapter(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tool.md"
            path.write_text("tool body", encoding="utf-8")

            text = tool_read_artifact.invoke({"artifact_hint": str(path)})

        self.assertIn("tool body", text)


if __name__ == "__main__":
    unittest.main()
