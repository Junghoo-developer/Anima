import unittest

from Core.graph import anima_app


class GraphCompileTests(unittest.TestCase):
    def test_graph_compiles(self):
        self.assertIsNotNone(anima_app)


if __name__ == "__main__":
    unittest.main()
