from app.api.routers.base import BaseApiRouter
from app.domain.models import ModelConfigCreate, ModelConfigPublic
from app.services.model_config import ModelConfigService

class ModelConfigRouter(BaseApiRouter):
    prefix = "/model_config"
    tags = ["模型配置"]
    service_cls = ModelConfigService
    create_schema_cls = ModelConfigCreate
    public_schema_cls = ModelConfigPublic

router = ModelConfigRouter().router