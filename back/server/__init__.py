# Lazy imports to avoid circular import issues
# Use: from server.app import create_app
# Instead of: from server import create_app

__all__ = ["create_app"]


def __getattr__(name: str):
    if name == "create_app":
        from server.app import create_app
        return create_app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
