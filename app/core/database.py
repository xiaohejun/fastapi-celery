from contextlib import contextmanager, AbstractContextManager
from typing import Any, Callable, Generator
import logging

from sqlalchemy import create_engine, orm
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from app.domain.models import BaseSQLModel
from app.core.settings import DatabaseSettings

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, settings: DatabaseSettings) -> None:
        assert isinstance(settings, DatabaseSettings), f"settings must be DatabaseSettings, but got {type(settings)}"
        self._engine = create_engine(settings.url, echo=settings.echo)
        self._session_factory = sessionmaker(
            autocommit=False,
            bind=self._engine,
        )

    def create_tables(self) -> None:
        BaseSQLModel.metadata.create_all(self._engine)

    def drop_tables(self) -> None:
        BaseSQLModel.metadata.drop_all(self._engine)

    @contextmanager
    def session(self) -> Generator[Session, Any, Any]:
        session: Session = self._session_factory()
        try:
            yield session
        except Exception:
            logger.exception("Session rollback because of exception")
            session.rollback()
            raise
        finally:
            session.close()


    @contextmanager
    def session_scope(self):
        """事务作用域上下文管理器"""
        print("enter session_scope")
        session: Session = self._session_factory()
        print("session created")
        try:
            print("yied session")
            yield session
            print("start commit session")
            session.commit()
            print("commit session")
        except Exception:
            print("rollback session")
            session.rollback()
            print("rollback session done")
            raise
        finally:
            print("start close session")
            session.close()
            print("end close session")