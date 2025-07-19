"""Repositories module."""

from typing import Iterator, TypeVar
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.models import TBaseSQLModel

class RepositoryNotFoundError(Exception):
    def __init__(self, entity_cls: type[TBaseSQLModel], entity_id: UUID):
        super().__init__(f"{entity_cls.__name__} not found, id: {entity_id}")


class BaseRepository:
    model_cls: type[TBaseSQLModel]

    def __init__(self, session: Session) -> None:
        assert isinstance(session, Session), f"session must be an instance of Session, but got {type(session)}"
        self.session = session

    def get_all(self) -> Iterator[TBaseSQLModel]:
        return self.session.query(self.model_cls).all()

    def get_by_id(self, entity_id: UUID) -> TBaseSQLModel:
        entity = self.session.get(self.model_cls, entity_id)
        if not entity:
            raise RepositoryNotFoundError(self.model_cls, entity_id)
        return entity

    def create(self, entity: TBaseSQLModel) -> TBaseSQLModel:
        entity = self.model_cls(**entity.model_dump())
        self.session.add(entity)
        self.session.flush([entity])
        self.session.refresh(entity)
        return entity

    def delete_by_id(self, entity_id: UUID) -> None:    
        entity: TBaseSQLModel = self.session.query(self.model_cls).filter(self.model_cls.id == entity_id).first()
        if not entity:
            raise RepositoryNotFoundError(self.model_cls, entity_id)
        self.session.delete(entity)
        self.session.flush()

TBaseRepository = TypeVar("TBaseRepository", bound=BaseRepository)

