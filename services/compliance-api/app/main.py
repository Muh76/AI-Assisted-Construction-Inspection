from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="Compliance API", lifespan=lifespan)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
