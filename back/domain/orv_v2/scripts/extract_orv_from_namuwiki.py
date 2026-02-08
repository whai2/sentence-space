"""
나무위키 데이터셋에서 전지적 독자 시점 정보 추출

Hugging Face의 heegyu/namuwiki 데이터셋에서
전지적 독자 시점 관련 문서를 검색하고 정보 추출
"""
import re
import json
from pathlib import Path
from datetime import datetime
from datasets import load_dataset
from typing import List, Dict


def search_orv_articles(dataset, keywords: List[str]) -> Dict[str, dict]:
    """
    전지적 독자 시점 관련 문서 검색

    Args:
        dataset: Hugging Face dataset (already split='train')
        keywords: 검색할 키워드 목록

    Returns:
        Dict[title, article_data]
    """
    results = {}

    print(f"🔍 전체 {len(dataset):,}개 문서 검색 중...")

    for idx, doc in enumerate(dataset):
        title = doc['title']
        text = doc['text']

        # 키워드 매칭
        for keyword in keywords:
            if keyword in title or keyword in text[:500]:  # 첫 500자만 검색
                results[title] = {
                    'title': title,
                    'text': text,
                    'contributors': doc['contributors'],
                    'matched_keyword': keyword
                }
                print(f"✅ 발견: {title} (키워드: {keyword})")
                break

        # 진행 상황 표시
        if (idx + 1) % 100000 == 0:
            print(f"   진행: {idx + 1:,} / {len(dataset):,}")

    return results


def extract_scenario_info(text: str) -> Dict:
    """
    나무위키 마크업에서 시나리오 정보 추출

    Args:
        text: 나무위키 마크업 텍스트

    Returns:
        추출된 시나리오 정보
    """
    info = {
        'title': None,
        'difficulty': None,
        'objective': None,
        'time_limit': None,
        'description': None,
        'phases': [],
        'characters': [],
        'events': []
    }

    # 제목 추출 (== ... == 형식)
    title_match = re.search(r'==\s*([^=\n]+?)\s*==', text)
    if title_match:
        info['title'] = title_match.group(1).strip()

    # 난이도 추출 (D급, C급 등)
    difficulty_match = re.search(r'([A-Z]급)', text)
    if difficulty_match:
        info['difficulty'] = difficulty_match.group(1)

    # 시간 제한 추출
    time_match = re.search(r'(\d+)분', text)
    if time_match:
        info['time_limit'] = int(time_match.group(1))

    # 목표 추출
    objective_patterns = [
        r'목표[:\s]+([^\n]+)',
        r'클리어 조건[:\s]+([^\n]+)',
        r'달성 조건[:\s]+([^\n]+)'
    ]
    for pattern in objective_patterns:
        objective_match = re.search(pattern, text)
        if objective_match:
            info['objective'] = objective_match.group(1).strip()
            break

    return info


def extract_character_info(text: str) -> Dict:
    """
    캐릭터 정보 추출

    Args:
        text: 나무위키 마크업 텍스트

    Returns:
        캐릭터 정보
    """
    info = {
        'name': None,
        'description': None,
        'personality': [],
        'abilities': [],
        'relationships': []
    }

    # 이름 추출
    name_match = re.search(r'==\s*([^=\n]+?)\s*==', text)
    if name_match:
        info['name'] = name_match.group(1).strip()

    # 설명 추출 (첫 번째 문단)
    desc_match = re.search(r'==.*?==\n\n([^\n]+)', text)
    if desc_match:
        info['description'] = desc_match.group(1).strip()

    return info


def save_results_to_json(results: Dict, output_dir: Path):
    """
    검색 결과를 JSON 파일로 저장

    Args:
        results: 검색 결과
        output_dir: 출력 디렉토리
    """
    # 타임스탬프
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 1. 개별 문서를 raw/ 디렉토리에 저장
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n💾 개별 문서 저장 중...")
    for title, data in results.items():
        # 파일명에서 특수문자 제거
        safe_filename = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')
        filepath = raw_dir / f"{safe_filename}.json"

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  ✅ {filepath.name}")

    # 2. 전체 결과를 하나의 파일로 저장
    summary_file = output_dir / f"extraction_summary_{timestamp}.json"
    summary_data = {
        "extracted_at": timestamp,
        "total_documents": len(results),
        "documents": list(results.keys()),
        "statistics": {
            "total_chars": sum(len(d['text']) for d in results.values()),
            "avg_chars": sum(len(d['text']) for d in results.values()) // len(results) if results else 0
        }
    }

    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 요약 파일 저장: {summary_file.name}")

    # 3. 가공된 데이터 저장 (processed/)
    processed_dir = output_dir / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    # 시나리오 정보 추출 및 저장
    if "전지적 독자 시점" in results or "가치 증명" in results:
        scenarios_file = processed_dir / "scenarios.json"
        scenarios = []

        for title, data in results.items():
            if "시나리오" in data['text'] or "가치" in title or "붉은 사막" in title:
                scenario_info = extract_scenario_info(data['text'])
                if scenario_info['title']:
                    scenario_info['source_document'] = title
                    scenarios.append(scenario_info)

        if scenarios:
            with open(scenarios_file, 'w', encoding='utf-8') as f:
                json.dump(scenarios, f, ensure_ascii=False, indent=2)
            print(f"✅ 시나리오 정보: {scenarios_file.name} ({len(scenarios)}개)")

    # 캐릭터 정보 추출 및 저장
    character_keywords = ["김독자", "유중혁", "이혜성", "비형"]
    characters_file = processed_dir / "characters.json"
    characters = []

    for title, data in results.items():
        if any(kw in title for kw in character_keywords):
            char_info = extract_character_info(data['text'])
            if char_info['name']:
                char_info['source_document'] = title
                characters.append(char_info)

    if characters:
        with open(characters_file, 'w', encoding='utf-8') as f:
            json.dump(characters, f, ensure_ascii=False, indent=2)
        print(f"✅ 캐릭터 정보: {characters_file.name} ({len(characters)}개)")

    print("\n" + "=" * 60)
    print(f"📦 저장 완료!")
    print(f"   위치: {output_dir.absolute()}")
    print("=" * 60)


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("📚 나무위키 데이터셋에서 전지적 독자 시점 정보 추출")
    print("=" * 60)

    # 1. 데이터셋 로드
    print("\n1️⃣ 데이터셋 로드 중...")
    print("⚠️  첫 실행 시 3GB 데이터셋 다운로드 (5-10분 소요)")
    try:
        dataset = load_dataset("heegyu/namuwiki", split="train", streaming=False)
        print(f"✅ 로드 완료: {len(dataset):,}개 문서")
    except Exception as e:
        print(f"❌ 로드 실패: {e}")
        print("\n해결 방법:")
        print("1. 인터넷 연결 확인")
        print("2. 디스크 여유 공간 확인 (3GB 이상 필요)")
        print("3. datasets 라이브러리 재설치: uv add datasets")
        return None

    # 2. 검색 키워드 정의
    keywords = [
        "전지적 독자 시점",
        "전독시",
        "김독자",
        "유중혁",
        "이혜성",
        "가치 증명",
        "붉은 사막",
        "도깨비 비형",
        "성좌",
        "시나리오 클리어"
    ]

    # 3. 문서 검색
    print(f"\n2️⃣ 키워드 검색: {', '.join(keywords)}")
    results = search_orv_articles(dataset, keywords)

    print(f"\n✅ 검색 완료: {len(results)}개 문서 발견")

    if not results:
        print("\n⚠️  검색 결과가 없습니다.")
        print("   키워드를 조정하거나 다른 방법을 시도해보세요.")
        return None

    # 4. 결과 출력
    print("\n" + "=" * 60)
    print("📊 검색 결과")
    print("=" * 60)

    for title, data in results.items():
        print(f"\n제목: {title}")
        print(f"매칭 키워드: {data['matched_keyword']}")
        print(f"본문 길이: {len(data['text']):,}자")
        print("-" * 60)

        # 본문 미리보기 (첫 200자)
        preview = data['text'][:200].replace('\n', ' ')
        print(f"미리보기: {preview}...")
        print()

    # 5. 상세 분석 (메인 문서)
    if "전지적 독자 시점" in results:
        print("\n" + "=" * 60)
        print("📖 '전지적 독자 시점' 메인 문서 분석")
        print("=" * 60)

        main_article = results["전지적 독자 시점"]['text']

        # 시나리오 관련 섹션 찾기
        scenario_sections = re.findall(
            r'(===?\s*시나리오.*?===?.*?)(?=\n===|$)',
            main_article,
            re.DOTALL
        )

        print(f"\n시나리오 섹션: {len(scenario_sections)}개 발견")
        for i, section in enumerate(scenario_sections[:3], 1):
            print(f"\n{i}. {section[:100]}...")

    # 6. JSON 저장
    print("\n" + "=" * 60)
    print("💾 JSON 파일로 저장 중...")
    print("=" * 60)

    # 현재 스크립트의 상위 디렉토리에서 data 폴더 찾기
    script_dir = Path(__file__).parent.parent.parent
    output_dir = script_dir / "data" / "namuwiki_orv"

    save_results_to_json(results, output_dir)

    return results


if __name__ == "__main__":
    print("\n" + "🚀 " * 20)
    print("전지적 독자 시점 나무위키 데이터 추출기")
    print("🚀 " * 20 + "\n")

    try:
        results = main()

        if results:
            print("\n\n" + "=" * 60)
            print("✨ 추출 완료!")
            print("=" * 60)
            print(f"\n다음 단계:")
            print("1. data/namuwiki_orv/raw/ 에서 개별 문서 확인")
            print("2. data/namuwiki_orv/processed/ 에서 가공된 데이터 확인")
            print("3. 필요시 Neo4j에 저장하는 스크립트 작성")
            print("\n" + "=" * 60)

    except ImportError as e:
        print(f"❌ 필수 라이브러리 누락: {e}")
        print("\n해결 방법:")
        print("   cd /Users/no-eunsu/hobby/sentence-space/back")
        print("   uv add datasets")
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자가 중단했습니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
