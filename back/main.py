import uvicorn

from server.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "server.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
