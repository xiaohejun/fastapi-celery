from fastapi import FastAPI
from app.api.routers.settings import router as settings_router
from app.api.routers.inference_sim_task import router as inference_sim_task_router
from app.api.routers.model_config import router as model_config_router

def register_routers(app: FastAPI) -> None:
    routers = [
        settings_router, 
        inference_sim_task_router,
        model_config_router
    ]
    for router in routers:
        app.include_router(router)