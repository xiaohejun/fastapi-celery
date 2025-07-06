"""Containers module."""

from dependency_injector import containers, providers
# from app.api.fastapi import FastAPIApp
from pathlib import Path

from app.core.settings import *
from app.core.database import Database
from app.repositories import TestRepository, UserRepository
from app.services import TestService, UserService

# class 

class Container(containers.DeclarativeContainer):

    wiring_config = containers.WiringConfiguration(packages=["app.api"])

    config = providers.Configuration(yaml_files=["config.yml"])
    config_filepath = Path(__file__).parent.parent.parent / "config.yml"
    config.from_yaml(filepath=config_filepath, required=True, envs_required=True)
    # config.set_yaml_files(["config.yml"])

    db = providers.Singleton(Database, settings=DatabaseSettings(**config.db()))

    # db_session
    # db_session = providers.Factory(db.provided.session)

    user_repository = providers.Factory(
        UserRepository,
        session_factory=db.provided.session,
    )

    user_service = providers.Factory(
        UserService,
        user_repository=user_repository,
    )

    # test_repository = providers.Factory(
    #     TestRepository,
    #     # session_factory=db.provided.session,
    # )

    # test_service = providers.Factory(
    #     TestService,
    #     test_repository=test_repository,
    # )


    # fastapi_app = providers.Singleton(FastAPIApp, settings=APISettings(**config.api()))

# container = Container()
# config = container.config()