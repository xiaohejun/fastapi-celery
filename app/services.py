"""Services module."""

from ast import List
from uuid import uuid4
from typing import Iterator

from sqlmodel import Session

from app.repositories import TestRepository, UserRepository
from app.domain.models import User, UserCreate

class BaseService: ...

    # @classmethod
    # def create_instance(cls, session: Session):
    #     return cls(session=session)

class UserService(BaseService):

    def __init__(self, user_repository: UserRepository) -> None:
        self._repository: UserRepository = user_repository

    def get_users(self) -> Iterator[User]:
        return self._repository.get_all()

    def get_user_by_id(self, user_id: int) -> User:
        return self._repository.get_by_id(user_id)

    def create_user(self) -> User:
        uid = uuid4()
        return self._repository.add(username=f"user_{uid}", email=f"{uid}@email.com", password="pwd")

    def delete_user_by_id(self, user_id: int) -> None:
        return self._repository.delete_by_id(user_id)
    
class TestService:
    def __init__(self, test_repository: TestRepository) -> None:
        self._repository: TestRepository = test_repository

    def get_all(self) -> Iterator[User]:
        return self._repository.get_all()