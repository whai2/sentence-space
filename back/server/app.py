from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )

    setup_middlewares(app)
    setup_routers(app)
    setup_events(app)

    return app


def setup_middlewares(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def setup_routers(app: FastAPI) -> None:
    from domain.example.routes import router as example_router
    from domain.world.routes import router as world_router
    from domain.orv.routes import router as orv_router
    from domain.orv_v2.routes import router as orv_v2_router
    from domain.orv_v3.routes import router as orv_v3_router
    from domain.myeolsal.routes import router as myeolsal_router
    from domain.scenario.routes import router as scenario_router
    from server.api.graph_routes import router as graph_router

    app.include_router(example_router, prefix="/api/v1")
    app.include_router(world_router, prefix="/api/v1")
    app.include_router(orv_router, prefix="/api/v1")
    app.include_router(orv_v2_router, prefix="/api")  # /api/orv/v2
    app.include_router(orv_v3_router, prefix="/api")  # /api/orv/v3
    app.include_router(myeolsal_router, prefix="/api")  # /api/myeolsal
    app.include_router(scenario_router, prefix="/api")  # /api/scenario
    app.include_router(graph_router)  # /api/graph


def setup_events(app: FastAPI) -> None:
    """Startup/Shutdown 이벤트 설정"""
    from domain.orv_v2.container import startup, shutdown

    @app.on_event("startup")
    async def on_startup():
        await startup()
        # 멸살법 서비스 초기화 (Pinecone이 비어있으면 시드 데이터 자동 로드)
        try:
            from domain.myeolsal.container import get_myeolsal_service
            service = get_myeolsal_service()
            result = await service.initialize(auto_seed=True)
            print(f"[Myeolsal] Initialized: {result}")
        except Exception as e:
            print(f"[Myeolsal] Init error: {e}")

        # 시나리오 설명집 초기화 (Neo4j에 시나리오 없으면 시드 데이터 자동 로드)
        try:
            from domain.scenario.container import get_scenario_service
            scenario_service = get_scenario_service()
            scenario_result = await scenario_service.initialize(auto_seed=True)
            print(f"[Scenario] Initialized: {scenario_result}")
        except Exception as e:
            print(f"[Scenario] Init error: {e}")

    @app.on_event("shutdown")
    async def on_shutdown():
        await shutdown()


app = create_app()
