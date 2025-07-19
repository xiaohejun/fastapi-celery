from sqlalchemy import UUID
from app.api.dependencies import get_service
from app.api.routers.base import BaseApiRouter
from app.domain.models import InferenceSimTaskCreate, InferenceSimTask
from app.services.inference_sim_task import InferenceSimTaskService

class InferenceSimTaskRouter(BaseApiRouter):
    prefix = "/inference_sim_tasks"
    tags = ["推理任务"]
    service_cls = InferenceSimTaskService
    create_schema_cls = InferenceSimTaskCreate
    public_schema_cls = InferenceSimTask


router = InferenceSimTaskRouter().router
