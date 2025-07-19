from app.domain.models import InferenceRuntimeConfig
from app.repositories.base import BaseRepository

class InferenceRuntimeConfigRepository(BaseRepository):
    model_cls = InferenceRuntimeConfig
