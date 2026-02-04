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

    app.include_router(example_router, prefix="/api/v1")
    app.include_router(world_router, prefix="/api/v1")
    app.include_router(orv_router, prefix="/api/v1")


app = create_app()
