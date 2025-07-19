from typing import Type
from fastapi import Depends
from app.core.database import Database
from app.core.dependencies import Container
from contextlib import contextmanager
from sqlalchemy.orm import Session

from app.services.base import TBaseService

def get_db() -> Database:
    return Container.db()

def get_db_session(
    db: Database = Depends(get_db)
):
    """数据库会话依赖项，管理整个请求的事务生命周期"""
    with db.session_scope() as session:
        yield session

def get_service(
    service_cls: Type[TBaseService],
):
    def _get_service(
        db_session: Session = Depends(get_db_session),
    ):
        return service_cls.create_instance(db_session)
    return Depends(_get_service)