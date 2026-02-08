"""
파서 디버깅 스크립트
"""
import json
import re
from pathlib import Path

# 파일 읽기
script_dir = Path(__file__).parent.parent.parent
input_file = script_dir / "data" / "namuwiki_orv" / "raw" / "전지적_독자_시점시나리오.json"

with open(input_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

raw_text = data['text']

print("=" * 60)
print("디버깅: 나무위키 시나리오 파싱")
print("=" * 60)
print(f"\n텍스트 길이: {len(raw_text)}")

# 1. 섹션 찾기
print("\n1️⃣ 섹션 매칭 테스트:")
section_pattern = r'== 8612 행성계\(지구\) =='
section_match = re.search(section_pattern, raw_text)
if section_match:
    print(f"✅ 8612 행성계 섹션 발견! 위치: {section_match.start()}")
    # 섹션 이후 500자 출력
    print(f"\n섹션 이후 500자:")
    print(raw_text[section_match.start():section_match.start() + 500])
else:
    print("❌ 8612 행성계 섹션을 찾을 수 없습니다.")
    # 전체 텍스트에서 "8612" 검색
    if "8612" in raw_text:
        pos = raw_text.find("8612")
        print(f"\n'8612' 문자열 발견! 위치: {pos}")
        print(f"주변 텍스트:")
        print(raw_text[max(0, pos-50):pos+100])

# 2. 메인 시나리오 패턴 테스트
print("\n\n2️⃣ 메인 시나리오 패턴 테스트:")
scenario_pattern = r"\* '''메인 시나리오 # ?(\d+)"
matches = list(re.finditer(scenario_pattern, raw_text))
print(f"발견된 메인 시나리오: {len(matches)}개")
for i, match in enumerate(matches[:5], 1):
    print(f"\n{i}. 위치 {match.start()}: {match.group(0)}")
    # 매치 이후 200자 출력
    print(f"   이후 200자: {raw_text[match.start():match.start() + 200]}")
