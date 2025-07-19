from app.domain.models import SystemConfig
from app.repositories.base import BaseRepository

class SystemConfigRepository(BaseRepository):
    model_cls = SystemConfig