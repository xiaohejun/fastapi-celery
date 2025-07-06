from fastapi import FastAPI
from app.api.routers.settings import router as settings_router
from app.api.routers.users import router as users_router
from app.api.routers.test import router as test_router

def register_routers(app: FastAPI) -> None:
    routers = [settings_router, users_router, test_router]
    for router in routers:
        app.include_router(router)