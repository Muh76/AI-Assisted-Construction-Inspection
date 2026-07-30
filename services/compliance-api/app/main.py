from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import engine
from app.routers import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="Compliance API", lifespan=lifespan)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()
