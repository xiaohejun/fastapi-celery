from fastapi import Depends
from app.core.database import Database
from app.core.dependencies import Container
from dependency_injector.wiring import Provide, inject
from contextlib import contextmanager

def get_db() -> Database:
    return Container.db()

def get_db_session(
    db: Database = Depends(get_db)
):
    """数据库会话依赖项，管理整个请求的事务生命周期"""
    with db.session_scope() as session:
        yield session