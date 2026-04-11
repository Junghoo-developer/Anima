# Core/u_function_engine.py

import math
import json
import ollama
from tools.toolbox import get_db_session

class UFunctionEngine:
    """
    [V6.1 심야 성찰 전용: 3차원 위상 공간 시맨틱 엔진]
    DB 조회와 임베딩 연산을 한 번만 수행하여 메모리에 캐싱하고,
    여러 종류의 U-함수 분석(정방향, 역방향, 3차원 교점)을 초고속으로 연속 수행합니다.
    """
    
    def __init__(self, track_type: str = "PastRecord", limit: int = 30):
        self.track_type = track_type
        self.limit = limit
        self.records = []          # 💡 DB에서 가져온 기록을 한 번만 저장하는 메모리 탄창!
        self.keyword_cache = {}    # 💡 한 번 임베딩한 검색어는 다시 Ollama를 부르지 않음!
        
        # 엔진 시동 시 즉시 탄창 장전!
        self._load_records_once()

    def _load_records_once(self):
        """DB에서 타겟 기록과 임베딩을 한 번만 긁어옵니다."""
        print(f"⚙️ [U-Engine] {self.track_type} {self.limit}개 기록 메모리 적재 중...")
        label = "Episode" if self.track_type == "Episode" else "PastRecord"
        query = f"""
        MATCH (n:{label})
        WHERE n.embedding IS NOT NULL
        RETURN n.id AS id, n.date AS date, n.content AS content, n.embedding AS embedding
        ORDER BY n.date DESC LIMIT $limit
        """
        try:
            with get_db_session() as session:
                data = session.run(query, limit=self.limit).data()
                data.reverse() # 시간순(과거->현재) 정렬
                self.records = data
                print(f"✅ [U-Engine] {len(self.records)}개 기록 장전 완료!")
        except Exception as e:
            print(f"🚨 DB 적재 에러: {e}")

    def _get_keyword_embedding(self, keyword: str):
        """키워드 임베딩을 구하되, 이미 구한 적 있으면 캐시에서 즉시 꺼냅니다."""
        if keyword not in self.keyword_cache:
            vec = ollama.embeddings(model='nomic-embed-text', prompt=keyword)['embedding']
            self.keyword_cache[keyword] = vec
        return self.keyword_cache[keyword]

    def _cosine_similarity(self, vec1, vec2):
        """1024차원 벡터 간의 수학적 거리 계산"""
        if not vec1 or not vec2 or len(vec1) != len(vec2): return 0.0
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm_a = math.sqrt(sum(a * a for a in vec1))
        norm_b = math.sqrt(sum(b * b for b in vec2))
        if norm_a == 0 or norm_b == 0: return 0.0
        return dot_product / (norm_a * norm_b)

    # =========================================================================
    # 🚀 [분석 무기고: 8a 요원이 맘대로 골라 쏘는 도구들]
    # =========================================================================

    def scan_3d_intersection(self, keyword_z: str, keyword_anti_z: str, keyword_y: str, threshold: float = 0.5) -> str:
        """[도구 1] 3차원 정반합 교점(임계점) 스캐너"""
        vec_z = self._get_keyword_embedding(keyword_z)
        vec_anti = self._get_keyword_embedding(keyword_anti_z)
        vec_y = self._get_keyword_embedding(keyword_y)
        
        leaf_nodes = []
        for r in self.records:
            vec_record = r['embedding']
            sim_z = self._cosine_similarity(vec_z, vec_record)
            sim_anti = self._cosine_similarity(vec_anti, vec_record)
            sim_y = self._cosine_similarity(vec_y, vec_record)
            
            # 교점(정/반 충돌) 또는 Y축 임계점 돌파 감지
            is_intersection = abs(sim_z - sim_anti) < 0.2 and sim_z > 0.3
            is_y_dominant = sim_y >= threshold
            
            if is_intersection or is_y_dominant:
                label = "Episode" if self.track_type == "Episode" else "PastRecord"
                leaf_nodes.append({
                    "id": r['id'], # 👈 DB의 절대 고유 ID!
                    "source_address": f"{label}|{r['date']}", # 👈 8b가 탯줄 연결할 때 쓸 공식 주소!
                    "date": r['date'],
                    "Z_score": round(sim_z, 3), 
                    "Anti_Z_score": round(sim_anti, 3), 
                    "Y_score": round(sim_y, 3),
                    "content_snippet": r['content'][:150] + "...",
                    "reason": "정/반 교차점" if is_intersection else f"Y축 임계점 초과"
                })
                
        return json.dumps({"scan_type": "3D_Intersection", "results": leaf_nodes}, ensure_ascii=False, indent=2)

    def scan_pure_shadow(self, keyword_z: str) -> str:
        """[도구 2] 역방향 U-함수 전용 (모순/흑역사/붕괴 탐지기)"""
        vec_z = self._get_keyword_embedding(keyword_z)
        
        shadow_nodes = []
        for r in self.records:
            vec_record = r['embedding']
            sim_z = self._cosine_similarity(vec_z, vec_record)
            
            # 💡 역함수 관용도: 목표 사상과 전혀 상관없거나 반대인 경우 (0.1 이하)
            if sim_z <= 0.15:
                shadow_nodes.append({
                    "date": r['date'],
                    "similarity": round(sim_z, 3),
                    "content_snippet": r['content'][:150] + "...",
                    "reason": "사상 붕괴 및 완전한 대척점 감지"
                })
                
        return json.dumps({"scan_type": "Inverse_Shadow", "results": shadow_nodes}, ensure_ascii=False, indent=2)
    
    # =========================================================================
    # 👇 [V7.2 Pro 긴급 용접 완료]: 주간 1차원 스캐너 (텍스트 차트 생성기)
    # =========================================================================

    def generate_text_trend_chart(self, keyword_z: str, track_type: str = "PastRecord") -> str:
        """[도구 3] 주간 체제 전용 1차원 스캐너: 시계열 트렌드 텍스트 차트 생성"""
        vec_z = self._get_keyword_embedding(keyword_z)
        lines = [f"📊 [{keyword_z}] 시계열 트렌드 분석 보고서 (데이터: {track_type})"]
        lines.append("※ 막대가 길수록 해당 날짜의 기록이 키워드와 깊은 연관이 있음을 의미합니다.\n")
        
        threshold = 0.3 
        hit_count = 0
        for r in self.records:
            sim = self._cosine_similarity(vec_z, r['embedding'])
            display_score = max(0.0, sim)
            bar_len = min(20, int(display_score * 20)) 
            bar = "█" * bar_len + "░" * (20 - bar_len)
            
            if sim >= threshold:
                lines.append(f"[{r.get('date', '?')}] {bar} ({sim:.3f}) | {r.get('content', '')[:35]}...")
                hit_count += 1
                
        if hit_count == 0: return f"❌ '{keyword_z}'에 대한 유의미한 트렌드를 찾을 수 없습니다."
        return "\n".join(lines)