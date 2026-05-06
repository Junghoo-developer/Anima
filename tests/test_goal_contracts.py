import unittest

from Core.goal_contracts import (
    contract_identity_names_from_facts,
    contract_status_packet,
    contract_satisfied_by_facts,
    derive_user_goal_contract,
    filled_slots_from_contract,
)


class GoalContractTests(unittest.TestCase):
    def test_user_name_goal_contract_requires_identity_slot(self):
        contract = derive_user_goal_contract("내 이름을 말해")
        self.assertEqual(contract["output_act"], "answer_identity_slot")
        self.assertEqual(contract["slot_to_fill"], "user.canonical_name")
        self.assertTrue(contract["evidence_required"])

    def test_deictic_memory_goal_contract_requires_referent_fact(self):
        contract = derive_user_goal_contract("네가 직접 그때의 상황을 떠올려봐")
        self.assertEqual(contract["output_act"], "answer_memory_recall")
        self.assertEqual(contract["slot_to_fill"], "memory.referent_fact")
        self.assertTrue(contract["evidence_required"])

    def test_question_surface_does_not_satisfy_memory_recall_slot(self):
        contract = derive_user_goal_contract("네가 직접 그때의 상황을 떠올려봐")
        facts = ["네가 써니였다면 어떻게 했을거야?"]
        self.assertFalse(contract_satisfied_by_facts(contract, facts))
        status, missing_slots, _ = contract_status_packet(contract, facts)
        self.assertEqual(status, "missing_slot")
        self.assertEqual(missing_slots, ["the specific remembered event being referenced"])

    def test_concrete_memory_fact_satisfies_memory_recall_slot(self):
        contract = derive_user_goal_contract("네가 직접 그때의 상황을 떠올려봐")
        facts = ["써니가 마리를 계단 아래로 밀쳤고 바질이 그 장면을 목격했다."]
        self.assertTrue(contract_satisfied_by_facts(contract, facts))
        filled = filled_slots_from_contract(contract, facts)
        self.assertEqual(filled["memory.referent_fact"], facts[:1])

    def test_friend_list_does_not_fill_user_name_slot(self):
        contract = derive_user_goal_contract("내 이름을 말해")
        facts = [
            "내 친구는 유준우, 박준영, 민시우, 임지우, 강지원도 있고 권우빈도 있다."
        ]
        self.assertFalse(contract_satisfied_by_facts(contract, facts))
        self.assertEqual(contract_identity_names_from_facts(facts), [])

    def test_identity_claim_fills_user_name_slot(self):
        contract = derive_user_goal_contract("내 이름을 말해")
        facts = ["사용자의 이름은 허정후다. 개발자는 허정후다."]
        self.assertTrue(contract_satisfied_by_facts(contract, facts))
        filled = filled_slots_from_contract(contract, facts)
        self.assertEqual(filled["user.canonical_name"], "허정후")


    def test_omori_identity_contract_stays_public_knowledge(self):
        contract = derive_user_goal_contract("Who is Sunny in OMORI?")
        self.assertEqual(contract["slot_to_fill"], "")
        self.assertEqual(contract["output_act"], "answer_narrative_fact")
        self.assertFalse(contract["evidence_required"])

    def test_omori_fictionality_contract_stays_public_knowledge(self):
        contract = derive_user_goal_contract("Is Sunny a fictional character in OMORI?")
        self.assertEqual(contract["slot_to_fill"], "")
        self.assertFalse(contract["evidence_required"])

    def test_omori_relationship_contract_stays_public_knowledge(self):
        contract = derive_user_goal_contract("Explain Sunny's relationship to OMORI.")
        self.assertEqual(contract["slot_to_fill"], "")
        self.assertFalse(contract["evidence_required"])

    def test_public_omori_contract_does_not_require_private_identity_slot(self):
        contract = derive_user_goal_contract("Who is Sunny in OMORI?")
        facts = ["Sunny stayed in his room for four years after the incident."]
        self.assertTrue(contract_satisfied_by_facts(contract, facts))
        self.assertEqual(contract["slot_to_fill"], "")

    def test_character_identity_slot_accepts_role_fact(self):
        contract = derive_user_goal_contract("Who is Sunny in OMORI?")
        facts = ["Sunny is one of the main OMORI characters and the protagonist of the game."]
        self.assertTrue(contract_satisfied_by_facts(contract, facts))

    def test_contract_status_packet_does_not_leak_internal_slot_names(self):
        contract = derive_user_goal_contract("Do you remember that event?")
        status, missing_slots, directive = contract_status_packet(contract, ["Do you remember that event?"])

        self.assertEqual(status, "missing_slot")
        self.assertNotIn("memory.referent_fact", " ".join(missing_slots))
        self.assertNotIn("memory.referent_fact", directive)

    def test_system_and_self_analysis_contracts_do_not_predeclare_slots(self):
        system_contract = derive_user_goal_contract("phase -1a loop bug를 설명해줘")
        analysis_contract = derive_user_goal_contract("내 가치관을 분석해줘")

        self.assertEqual(system_contract["output_act"], "diagnose_system")
        self.assertEqual(system_contract["slot_to_fill"], "")
        self.assertEqual(analysis_contract["output_act"], "self_analysis_snapshot")
        self.assertEqual(analysis_contract["slot_to_fill"], "")


if __name__ == "__main__":
    unittest.main()
