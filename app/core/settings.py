from pydantic_settings import BaseSettings

class APISettings(BaseSettings):
    title: str
    version: str
    description: str
    host: str
    port: int
    host_port: int

class DatabaseSettings(BaseSettings):
    url: str
    echo: bool

# class CelerySettings(BaseSettings):
#     broker_url: str
#     result_backend: str
#     include: list[str] = ["app.tasks"]

# class Settings(BaseSettings):
#     api: APISettings = APISettings()
#     db: DatabaseSettings = DatabaseSettings()
#     celery: CelerySettings = CelerySettings()

#     class Config:
#         env_file = ".env"
#         env_file_encoding = "utf-8"
