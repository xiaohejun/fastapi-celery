from app.domain.models import InferenceSimTask
from app.repositories.base import BaseRepository

class InferenceSimTaskRepository(BaseRepository):
    model_cls = InferenceSimTask
