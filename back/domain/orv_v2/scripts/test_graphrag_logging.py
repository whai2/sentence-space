"""
GraphRAG 로깅 테스트 스크립트

프론트엔드 API 호출을 시뮬레이션하여 GraphRAG가 실제로 사용되는지 확인
"""
import asyncio
import logging
import sys
from pathlib import Path

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# 도메인별 로거 레벨 설정
logging.getLogger("domain.orv_v2.agents.graph_rag_retriever").setLevel(logging.DEBUG)
logging.getLogger("domain.orv_v2.agents.story_planner").setLevel(logging.INFO)
logging.getLogger("domain.orv_v2.graph.workflow").setLevel(logging.INFO)
logging.getLogger("domain.orv_v2.service.game_service").setLevel(logging.INFO)
logging.getLogger("domain.orv_v2.routes.game_routes").setLevel(logging.INFO)

logger = logging.getLogger(__name__)


async def test_graphrag_workflow():
    """
    GraphRAG 워크플로우 테스트

    실제 API 호출과 동일한 흐름을 시뮬레이션합니다.
    """
    from domain.orv_v2.container import get_game_service

    print("=" * 80)
    print("🧪 GraphRAG 로깅 테스트")
    print("=" * 80)

    try:
        # 1. 게임 서비스 가져오기
        logger.info("📦 컨테이너에서 게임 서비스 로드 중...")
        service = get_game_service()

        # 2. 새 세션 생성
        logger.info("\n1️⃣ 새 게임 세션 생성...")
        session_result = await service.create_session()
        session_id = session_result["session_id"]
        logger.info(f"✅ 세션 생성 완료: {session_id}")

        # 3. Auto-Narrative 진행 (GraphRAG가 호출되는 시점)
        logger.info("\n2️⃣ Auto-Narrative 진행 (GraphRAG 호출 예상)...")
        print("\n" + "=" * 80)
        print("🔍 아래 로그에서 GraphRAG 사용 여부를 확인하세요:")
        print("   - [GraphRAG] 시나리오 지식 검색 시작")
        print("   - [StoryPlanner] 스토리 플랜 생성 시작")
        print("=" * 80 + "\n")

        result = await service.continue_auto_narrative(session_id)

        print("\n" + "=" * 80)
        if result["success"]:
            logger.info(f"✅ Auto-Narrative 완료")
            logger.info(f"   - 서술: {result['narrative'][:100]}...")
            logger.info(f"   - 선택지 개수: {len(result['choices'])}")
        else:
            logger.error(f"❌ Auto-Narrative 실패: {result.get('error')}")

        # 4. 세션 삭제 (정리)
        logger.info("\n3️⃣ 테스트 세션 삭제...")
        await service.delete_session(session_id)
        logger.info("✅ 세션 삭제 완료")

        print("\n" + "=" * 80)
        print("✨ 테스트 완료!")
        print("=" * 80)
        print("\n💡 로그 확인 포인트:")
        print("   1. [Workflow] GraphRAG 호출: scenario_id=xxx")
        print("   2. [GraphRAG] 시나리오 지식 검색 시작")
        print("   3. [GraphRAG] Neo4j 데이터 조회 완료")
        print("   4. [GraphRAG] 시나리오 컨텍스트 생성 완료")
        print("\n   위 로그들이 보이면 GraphRAG가 정상 작동하는 것입니다!")
        print("=" * 80)

    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(test_graphrag_workflow())
