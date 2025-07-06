from fastapi import APIRouter, Depends, HTTPException
from dependency_injector.wiring import Provide, inject
from app.core.dependencies import Container
from sqlalchemy.orm import Session
from app.api.dependencies import get_db_session

from app.services import TestService

router = APIRouter(
    prefix="/test",
    tags=["test"],
)

# @router.get("/")
# @inject
# def get_all(test_service: TestService = Depends(Container.test_service)):
#     return test_service.get_all()
from app.worker import create_task

@router.post("/")
def test(
    session: Session = Depends(get_db_session)  # 注入会话依赖
):
    task = create_task.delay(1)
    print(task.id)
    return {"task_id": task.id, "task_status": task.state}
