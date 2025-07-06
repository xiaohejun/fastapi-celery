from contextlib import asynccontextmanager
from logging import config
import uvicorn
from app.api.middleware import register_middleware
from app.core.dependencies import Container
from fastapi import FastAPI
from app.api.routers import register_routers
from app.core.settings import APISettings


def create_app() -> FastAPI:

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        container = app.state.container
        container.db().create_tables()
        yield
        container.db().drop_tables()

    container = Container()
    api_settings = APISettings(**container.config()["api"])
    app = FastAPI(
        title=api_settings.title,
        description=api_settings.description,
        version=api_settings.version,
        lifespan=lifespan
    )
    app.state.container = container
    register_routers(app)
    register_middleware(app)
    return app

fastapi_app = create_app()

if __name__ == "__main__":
    config = fastapi_app.state.container.config()["api"]
    uvicorn.run(
        "app.api.main:fastapi_app",
        host=config["host"],
        port=config["port"],
        reload=True,
        reload_dirs=["."],
    )
