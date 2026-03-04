import os

# 1. 이 파일이 있는 진짜 위치(tools 폴더)를 찾음
current_folder = os.path.dirname(os.path.abspath(__file__))

print(f"📂 파이썬이 서 있는 곳: {current_folder}")
print("👇 제 눈(Python)에 보이는 파일들은 이렇습니다:")
print("-" * 30)

# 2. 그 폴더 안에 있는 모든 파일 이름을 출력
files = os.listdir(current_folder)

for file_name in files:
    print(f"📄 {file_name}")

print("-" * 30)