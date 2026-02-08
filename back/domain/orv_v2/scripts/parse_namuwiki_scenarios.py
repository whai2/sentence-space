"""
나무위키 마크업에서 시나리오 정보 파싱

전지적_독자_시점시나리오.json 파일의 나무위키 마크업을 파싱하여
구조화된 시나리오 데이터로 변환
"""
import re
import json
from pathlib import Path
from typing import List, Dict, Optional


class NamuwikiScenarioParser:
    """나무위키 시나리오 마크업 파서"""

    def __init__(self, raw_text: str):
        """
        Args:
            raw_text: 나무위키 마크업 텍스트
        """
        self.raw_text = raw_text
        self.scenarios = []

    def parse(self) -> List[Dict]:
        """
        나무위키 마크업을 파싱하여 시나리오 목록 반환

        Returns:
            List[Dict]: 파싱된 시나리오 목록
        """
        # 메인 시나리오 섹션 찾기
        main_scenario_section = re.search(
            r'== 8612 행성계\(지구\) ==(.*?)(?=\n== [^=]|$)',
            self.raw_text,
            re.DOTALL
        )

        if not main_scenario_section:
            print("⚠️  8612 행성계 섹션을 찾을 수 없습니다.")
            return []

        section_text = main_scenario_section.group(1)
        print(f"✅ 8612 행성계 섹션 발견! 길이: {len(section_text)}자")

        # 메인 시나리오 추출
        self._parse_main_scenarios(section_text)

        # 서브 시나리오 추출
        self._parse_sub_scenarios(section_text)

        # 히든 시나리오 추출
        self._parse_hidden_scenarios(section_text)

        return self.scenarios

    def _parse_main_scenarios(self, text: str):
        """메인 시나리오 파싱"""
        # 패턴: * '''메인 시나리오 # N ― 제목'''
        pattern = r"\* '''메인 시나리오 # ?(\d+)\s*[―\-]\s*(.+?)'''"

        for match in re.finditer(pattern, text):
            scenario_num = match.group(1)
            scenario_title = match.group(2).strip()

            # 매치 위치 이후에서 테이블 찾기
            remaining_text = text[match.end():]

            # 다음 시나리오 제목까지의 텍스트만 추출
            next_scenario = re.search(r'\n \* \'\'\'', remaining_text)
            if next_scenario:
                section_text = remaining_text[:next_scenario.start()]
            else:
                section_text = remaining_text[:1000]

            # 테이블 파싱: ||<table>...||
            table_match = re.search(
                r'\|\|<table[^>]*>(.*?)\|\|',
                section_text,
                re.DOTALL
            )

            if table_match:
                table_content = table_match.group(1)
                scenario_data = self._parse_scenario_table(
                    scenario_num,
                    scenario_title,
                    table_content,
                    "main"
                )

                # 설명 텍스트 추출 (테이블 다음의 텍스트)
                desc_start = table_match.end()
                desc_text = self._extract_description(section_text, desc_start)
                scenario_data['description'] = desc_text

                self.scenarios.append(scenario_data)

    def _parse_sub_scenarios(self, text: str):
        """서브 시나리오 파싱"""
        # 서브 시나리오 섹션 찾기
        sub_section = re.search(
            r'=== 서브 시나리오 ===(.*?)(?:===|$)',
            text,
            re.DOTALL
        )

        if not sub_section:
            return

        sub_text = sub_section.group(1)
        pattern = r"\* '''<서브 시나리오 - (.+?)>'''"

        for match in re.finditer(pattern, sub_text):
            scenario_title = match.group(1).strip()

            # 매치 위치 이후에서 테이블 찾기
            remaining_text = sub_text[match.end():]

            # 다음 시나리오 제목까지의 텍스트만 추출
            next_scenario = re.search(r'\n \* \'\'\'', remaining_text)
            if next_scenario:
                section_text = remaining_text[:next_scenario.start()]
            else:
                section_text = remaining_text[:1000]

            table_match = re.search(
                r'\|\|<table[^>]*>(.*?)\|\|',
                section_text,
                re.DOTALL
            )

            if table_match:
                table_content = table_match.group(1)
                scenario_data = self._parse_scenario_table(
                    None,
                    scenario_title,
                    table_content,
                    "sub"
                )

                # 설명 추가
                desc_start = table_match.end()
                desc_text = self._extract_description(section_text, desc_start)
                scenario_data['description'] = desc_text

                self.scenarios.append(scenario_data)

    def _parse_hidden_scenarios(self, text: str):
        """히든 시나리오 파싱"""
        # 히든 시나리오 섹션 찾기
        hidden_section = re.search(
            r'=== 히든 시나리오 ===(.*?)(?:===|==|$)',
            text,
            re.DOTALL
        )

        if not hidden_section:
            return

        hidden_text = hidden_section.group(1)
        pattern = r"\* '''<히든 시나리오 [―\-] (.+?)>'''"

        for match in re.finditer(pattern, hidden_text):
            scenario_title = match.group(1).strip()

            # 매치 위치 이후에서 테이블 찾기
            remaining_text = hidden_text[match.end():]

            # 다음 시나리오 제목까지의 텍스트만 추출
            next_scenario = re.search(r'\n \* \'\'\'', remaining_text)
            if next_scenario:
                section_text = remaining_text[:next_scenario.start()]
            else:
                section_text = remaining_text[:1000]

            table_match = re.search(
                r'\|\|<table[^>]*>(.*?)\|\|',
                section_text,
                re.DOTALL
            )

            if table_match:
                table_content = table_match.group(1)
                scenario_data = self._parse_scenario_table(
                    None,
                    scenario_title,
                    table_content,
                    "hidden"
                )

                # 설명 추가
                desc_start = table_match.end()
                desc_text = self._extract_description(section_text, desc_start)
                scenario_data['description'] = desc_text

                self.scenarios.append(scenario_data)

    def _parse_scenario_table(
        self,
        scenario_num: Optional[str],
        title: str,
        table_content: str,
        scenario_type: str
    ) -> Dict:
        """시나리오 테이블 파싱"""
        data = {
            "scenario_id": f"scenario_{scenario_num}" if scenario_num else None,
            "scenario_number": int(scenario_num) if scenario_num and scenario_num.isdigit() else None,
            "title": title,
            "type": scenario_type,
            "difficulty": None,
            "clear_condition": None,
            "time_limit": None,
            "reward": None,
            "failure_penalty": None,
            "description": None
        }

        # 각 필드 파싱
        # 분류
        category_match = re.search(r'분류\s*[:：]\s*(\w+)', table_content)
        if category_match:
            data['category'] = category_match.group(1)

        # 난이도
        difficulty_match = re.search(r'난이도\s*[:：]\s*([^\n]+)', table_content)
        if difficulty_match:
            data['difficulty'] = difficulty_match.group(1).strip()

        # 클리어 조건
        clear_match = re.search(
            r'클리어 조건\s*[:：]\s*([^\n]+(?:\n(?!\w+\s*[:：])[^\n]+)*)',
            table_content,
            re.MULTILINE
        )
        if clear_match:
            condition = clear_match.group(1).strip()
            # 각주 제거
            condition = re.sub(r'\[\*[^\]]+\]', '', condition)
            # 펼치기 제거
            condition = re.sub(r'\{\{\{#!folding.*?\}\}\}', '', condition, flags=re.DOTALL)
            data['clear_condition'] = condition.strip()

        # 제한시간
        time_match = re.search(r'제한시간\s*[:：]\s*([^\n]+)', table_content)
        if time_match:
            time_str = time_match.group(1).strip()
            data['time_limit'] = time_str

            # 분 단위로 변환
            if '분' in time_str:
                minutes = re.search(r'(\d+)분', time_str)
                if minutes:
                    data['time_limit_minutes'] = int(minutes.group(1))
            elif '일' in time_str:
                days = re.search(r'(\d+)일', time_str)
                if days:
                    data['time_limit_days'] = int(days.group(1))
            elif '시간' in time_str:
                hours = re.search(r'(\d+)시간', time_str)
                if hours:
                    data['time_limit_hours'] = int(hours.group(1))

        # 보상
        reward_match = re.search(r'보상\s*[:：]\s*([^\n]+)', table_content)
        if reward_match:
            reward_str = reward_match.group(1).strip()
            data['reward'] = reward_str

            # 코인 추출
            coins = re.search(r'([\d,]+)\s*코인', reward_str)
            if coins:
                data['reward_coins'] = int(coins.group(1).replace(',', ''))

        # 실패 시
        failure_match = re.search(r'실패\s*시?\s*[:：]\s*([^\n]+)', table_content)
        if failure_match:
            data['failure_penalty'] = failure_match.group(1).strip()

        return data

    def _extract_description(self, text: str, start_pos: int) -> str:
        """
        시나리오 설명 추출

        테이블 다음의 텍스트를 추출 (다음 시나리오 또는 섹션까지)
        """
        # 다음 시나리오나 섹션까지의 텍스트 추출
        next_scenario = re.search(
            r'\n\s*\* \'\'\'',
            text[start_pos:]
        )

        if next_scenario:
            desc_text = text[start_pos:start_pos + next_scenario.start()]
        else:
            desc_text = text[start_pos:start_pos + 500]  # 최대 500자

        # 정리
        desc_text = desc_text.strip()
        # 각주 제거
        desc_text = re.sub(r'\[\*[^\]]+\]', '', desc_text)
        # 빈 줄 제거
        desc_text = re.sub(r'\n\s*\n', '\n', desc_text)

        return desc_text[:300] if desc_text else None  # 최대 300자


def parse_namuwiki_scenarios(input_file: Path, output_file: Path):
    """
    나무위키 시나리오 파일 파싱

    Args:
        input_file: 입력 파일 (전지적_독자_시점시나리오.json)
        output_file: 출력 파일 (parsed_scenarios.json)
    """
    print("=" * 60)
    print("📖 나무위키 시나리오 파싱")
    print("=" * 60)

    # 1. 입력 파일 읽기
    print(f"\n1️⃣ 입력 파일 읽기: {input_file.name}")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    raw_text = data['text']
    print(f"✅ 텍스트 길이: {len(raw_text):,}자")

    # 2. 파싱
    print("\n2️⃣ 시나리오 파싱 중...")
    parser = NamuwikiScenarioParser(raw_text)
    scenarios = parser.parse()

    print(f"✅ 파싱 완료: {len(scenarios)}개 시나리오")

    # 3. 통계
    print("\n📊 파싱 통계:")
    main_count = sum(1 for s in scenarios if s['type'] == 'main')
    sub_count = sum(1 for s in scenarios if s['type'] == 'sub')
    hidden_count = sum(1 for s in scenarios if s['type'] == 'hidden')

    print(f"  - 메인 시나리오: {main_count}개")
    print(f"  - 서브 시나리오: {sub_count}개")
    print(f"  - 히든 시나리오: {hidden_count}개")

    # 4. 샘플 출력
    print("\n📝 샘플 (첫 3개):")
    for i, scenario in enumerate(scenarios[:3], 1):
        print(f"\n{i}. [{scenario['type']}] {scenario['title']}")
        print(f"   난이도: {scenario['difficulty']}")
        print(f"   클리어: {scenario['clear_condition'][:50] if scenario['clear_condition'] else 'N/A'}...")

    # 5. 저장
    print(f"\n3️⃣ 결과 저장: {output_file.name}")
    output_data = {
        "total_scenarios": len(scenarios),
        "main_scenarios": main_count,
        "sub_scenarios": sub_count,
        "hidden_scenarios": hidden_count,
        "scenarios": scenarios
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print("✅ 저장 완료!")

    print("\n" + "=" * 60)
    print("✨ 파싱 완료!")
    print("=" * 60)

    return scenarios


if __name__ == "__main__":
    # 경로 설정
    script_dir = Path(__file__).parent.parent.parent
    input_file = script_dir / "data" / "namuwiki_orv" / "raw" / "전지적_독자_시점시나리오.json"
    output_file = script_dir / "data" / "namuwiki_orv" / "processed" / "parsed_scenarios.json"

    if not input_file.exists():
        print(f"❌ 입력 파일이 없습니다: {input_file}")
        print("\n먼저 extract_orv_from_namuwiki.py를 실행하세요.")
        exit(1)

    parse_namuwiki_scenarios(input_file, output_file)
