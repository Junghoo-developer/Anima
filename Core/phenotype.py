import sys
import os

# [수정] 도구함(utils)에서 ROI 계산기 가져오기
try:
    from Core.utils import calculate_roi
except ImportError:
    # 경로 문제 생기면 바로 옆에서 찾기
    from utils import calculate_roi

class Phenotype:
    def __init__(self, gene):
        self.gene = gene
        self.stats = {} 
        
        # [금융 장부] 누적 수입/지출 기록용
        self._financial_ledger = {
            "total_income": 0.0,
            "total_expense": 0.0
        }
        
        self._build_body()

    def _build_body(self):
        """DNA 설계도(JSON)를 보고 변수 초기화"""
        self.stats["survival_order"] = {}
        for key in self.gene.survival_order_keys:
            if key == "token_budget":
                val = 100.0
            elif key == "rate_profit":
                val = 0.0   # 0%
            elif key == "safety":
                val = 100.0
            elif key == "rate_connecting":
                val = 100.0
            else:
                val = 50.0
            self.stats["survival_order"][key] = val

        self.stats["survival_state"] = {}
        for key in self.gene.survival_state_keys:
            if key == "energy":
                val = 100.0
            elif key == "valence":
                val = 0.0
            else:
                val = 0.0
            self.stats["survival_state"][key] = val

    def update_finance(self, income, expense):
        """
        [금융 업데이트] 
        도구함(utils)의 계산기를 빌려와서 정확하게 수익률을 갱신함.
        """
        # 1. 장부에 기록 (누적)
        self._financial_ledger["total_income"] += income
        self._financial_ledger["total_expense"] += expense
        
        # 2. 계산기(Utils) 사용! (중복 제거됨) ✨
        current_roi = calculate_roi(
            self._financial_ledger["total_income"], 
            self._financial_ledger["total_expense"]
        )
            
        # 3. 결과 반영
        self.stats["survival_order"]["rate_profit"] = current_roi
        
        return current_roi

    def update(self, category, key, delta):
        """일반 변수 업데이트"""
        if category in self.stats and key in self.stats[category]:
            current = self.stats[category][key]
            
            if key == "rate_profit":
                 new_val = current + delta 
            elif key == "valence":
                 new_val = max(-100.0, min(100.0, current + delta))
            else:
                 new_val = max(0.0, min(100.0, current + delta))

            self.stats[category][key] = new_val
            return new_val
        return None

    def get_value(self, category, key):
        return self.stats.get(category, {}).get(key, 0.0)
    
    def get_all_status(self):
        """
        현재 송련이의 모든 생체 스탯을 딕셔너리로 반환 (박제용)
        """
        return self.stats