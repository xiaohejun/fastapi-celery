from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from dependency_injector.wiring import Provide, inject
from sqlalchemy.orm import Session

from app.core.dependencies import Container
from app.domain.models import User, UserCreate
from app.repositories import NotFoundError
from app.services import UserService

router = APIRouter(
    prefix="/users",
    tags=["users"],
)

# Depends(Provide[Container.db.provided.session])
# @inject
# def get_db_session(session_factory: Provide[Container.db.provided.session]):
#     return {"1": "2"}


# @router.post("/test")
# # @inject
# def test(session = Depends(get_db_session)):
#     return {"message": f"{type(session)}"}

@router.get("/get_all")
@inject
def get_list(
    user_service: Annotated[UserService, Depends(Provide[Container.user_service])],
):
    print(f"type {type(user_service)}")
    return user_service.get_users()


@router.get("/{user_id}")
@inject
def get_by_id(
    user_id: int,
    user_service: Annotated[UserService, Depends(Provide[Container.user_service])],
):
    try:
        return user_service.get_user_by_id(user_id)
    except NotFoundError:
        return Response(status_code=status.HTTP_404_NOT_FOUND)


@router.post("/create", status_code=status.HTTP_201_CREATED)
@inject
def add(
    user_service: Annotated[UserService, Depends(Provide[Container.user_service])],
) -> User:
    return user_service.create_user()


@router.delete("/delete/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
def remove(
    user_id: int,
    user_service: Annotated[UserService, Depends(Provide[Container.user_service])],
) -> Response:
    try:
        user_service.delete_user_by_id(user_id)
    except NotFoundError:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    else:
        return Response(status_code=status.HTTP_204_NO_CONTENT)