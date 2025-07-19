from app.domain.models import ModelConfig
from app.repositories.base import BaseRepository

class ModelConfigRepository(BaseRepository):
    model_cls = ModelConfig