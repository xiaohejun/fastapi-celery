from app.repositories.model_config import ModelConfigRepository
from app.services.base import BaseService

class ModelConfigService(BaseService):
    repository_cls = ModelConfigRepository