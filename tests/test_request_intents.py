import unittest

from Core.request_intents_v4 import (
    classify_requested_assistant_move,
    extract_explicit_search_phrase,
)


class RequestIntentHelperTests(unittest.TestCase):
    def test_requested_assistant_move_classifier_is_retired(self):
        self.assertEqual(classify_requested_assistant_move("ask me a question"), "")
        self.assertEqual(classify_requested_assistant_move("네가 직접 알아봐"), "")

    def test_explicit_search_phrase_uses_clean_utf8_patterns(self):
        self.assertEqual(
            extract_explicit_search_phrase('검색 "써니와 오모리" 결과 말해줘'),
            "써니와 오모리",
        )
        self.assertEqual(
            extract_explicit_search_phrase("OMORI라고 검색해줘"),
            "OMORI",
        )


if __name__ == "__main__":
    unittest.main()
