from fastapi import APIRouter, Depends, Request

from app.core.dependencies import Container

router = APIRouter(
    prefix="/settings",
    tags=["settings"],
)

def get_container(request: Request) -> Container:
    return request.app.state.container

@router.get("/")
async def get_settings(container: Container = Depends(get_container)):
    return container.config()