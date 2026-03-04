import json
import os
import sys

class Gene:
    def __init__(self, config_path=None):
        # 경로 자동 탐색
        if config_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            config_path = os.path.join(project_root, "SEED", "dna_config.json")

        self.dna_data = {}
        
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                self.dna_data = json.load(f)
        else:
            print(f"🚨 [ERROR] DNA 파일 없음: {config_path}")
            sys.exit(1)

        # 생존 변수 파싱
        self.survival_value = self.dna_data.get("survival_value", {})
        self.survival_order_keys = self.survival_value.get("survival_order", [])
        self.survival_state_keys = self.survival_value.get("survival_state", [])