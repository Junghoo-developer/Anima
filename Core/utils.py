import time

# ---------------------------------------------------------
# 1. 비용 계산기 (토큰 -> 돈)
# ---------------------------------------------------------
def get_token_count(text):
    """
    [비용 계산] 텍스트를 입력하면 예상되는 토큰 수를 반환.
    """
    if not text:
        return 0

    try:
        import tiktoken
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except ImportError:
        # 라이브러리 없으면 글자 수 * 0.8 (비상용)
        return int(len(text) * 0.8)

# ---------------------------------------------------------
# 2. 수익률 계산기 (투자 대비 소득, ROI)
# ---------------------------------------------------------
def calculate_roi(income, expense):
    """
    [수익률 계산] 
    - 들어온 돈(income)과 개발자간 돈(expense)을 비교해 효율(%)을 계산함.
    - 100%가 본전, 200%면 2배 이득.
    """
    if expense == 0:
        if income > 0: return 999.0 # 돈 안 쓰고 벌었으면 개이득 (무한대)
        return 0.0 # 둘 다 0이면 변화 없음
        
    roi = (income / expense) * 100.0
    return round(roi, 2) # 소수점 둘째 자리까지 깔끔하게

# ---------------------------------------------------------
# 3. 접속 빈도 계산기 (시간 감지)
# ---------------------------------------------------------
def get_time_gap(last_timestamp):
    """
    [빈도 계산]
    - 마지막 접속 시간(timestamp)을 주면, 지금으로부터 몇 분 지났는지 알려줌.
    - 이 시간이 짧을수록 '접속 빈도'가 높은 것.
    """
    if last_timestamp is None:
        return 0.0 # 처음 만남
        
    current_time = time.time()
    gap_seconds = current_time - last_timestamp
    gap_minutes = gap_seconds / 60.0
    
    return round(gap_minutes, 1) # 10.5분 지남

# ---------------------------------------------------------
# [테스트] 사장님 검수용
# ---------------------------------------------------------
if __name__ == "__main__":
    # 1. 토큰 테스트
    print(f"💰 토큰 비용: {get_token_count('사장님 퇴근하고 싶어요')}개")
    
    # 2. 수익률 테스트 (50원 쓰고 150원 벌었다면?)
    roi = calculate_roi(150, 50)
    print(f"📈 수익률: {roi}% (300%면 3배 뻥튀기 성공)")
    
    # 3. 시간 테스트 (방금 전과 지금 차이)
    now = time.time()
    time.sleep(1) # 1초 쉼
    print(f"⏱️ 시간 차이: {get_time_gap(now)}분 (아주 짧음)")