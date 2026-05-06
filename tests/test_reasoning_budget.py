import unittest

from Core.nodes import _resolve_reasoning_budget
from Core.state import empty_anima_state


class ReasoningBudgetTests(unittest.TestCase):
    def test_resolved_state_zero_is_preserved_after_plan_exists(self):
        state = empty_anima_state()
        state["reasoning_plan"] = {"reasoning_budget": 0, "preferred_path": "delivery_contract"}
        state["reasoning_budget"] = 0
        self.assertEqual(_resolve_reasoning_budget(state, {"reasoning_budget": 2}), 0)

    def test_plan_reasoning_budget_is_used_when_state_missing(self):
        state = empty_anima_state()
        self.assertEqual(_resolve_reasoning_budget(state, {"reasoning_budget": 2}), 2)

    def test_plan_zero_is_preserved_when_state_missing(self):
        state = empty_anima_state()
        self.assertEqual(_resolve_reasoning_budget(state, {"reasoning_budget": 0}), 0)

    def test_legacy_budget_key_is_still_supported(self):
        state = empty_anima_state()
        self.assertEqual(_resolve_reasoning_budget(state, {"budget": 3}), 3)

    def test_invalid_values_fall_back_to_default(self):
        state = empty_anima_state()
        state["reasoning_budget"] = None
        self.assertEqual(_resolve_reasoning_budget(state, {"reasoning_budget": "bad"}, default=1), 1)


if __name__ == "__main__":
    unittest.main()
