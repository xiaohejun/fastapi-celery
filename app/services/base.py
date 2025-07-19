from typing import TypeVar
from sqlalchemy.orm import Session
from app.repositories.base import TBaseRepository
from uuid import UUID
from app.domain.models import InferenceSimTask, TBaseSQLModel

class BaseService:
    repository_cls: type[TBaseRepository]

    def __init__(self, repository: TBaseRepository):
        self.repository = repository

    @classmethod
    def create_instance(cls, session: Session):
        return cls(cls.repository_cls(session))

    def get_all(self):
        return self.repository.get_all()

    def get_by_id(self, entity_id: UUID):
        return self.repository.get_by_id(entity_id)
    
    def create(self, entity: TBaseSQLModel):
        return self.repository.create(entity)
    
    def delete_by_id(self, entity_id: UUID):
        return self.repository.delete_by_id(entity_id)
    
    

TBaseService = TypeVar('TBaseService', bound=BaseService)