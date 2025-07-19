from uuid import UUID
from app.domain.models import InferenceRuntimeConfig, InferenceSimTaskCreate, InferenceSimTask, ModelConfig, SystemConfig
from app.repositories.inference_runtime_config import InferenceRuntimeConfigRepository
from app.repositories.inference_sim_task import InferenceSimTaskRepository
from app.repositories.model_config import ModelConfigRepository
from app.repositories.system_config import SystemConfigRepository
from app.services.base import BaseService
from app.worker.inference_sim_task import run_task

class InferenceSimTaskService(BaseService):
    repository_cls = InferenceSimTaskRepository

    def create(self, inference_sim_task: InferenceSimTaskCreate) -> InferenceSimTask:
        model_config_ = ModelConfig(
            **inference_sim_task.model_config_.model_dump()
        )
        system_config = SystemConfig(
            **inference_sim_task.system_config.model_dump()
        )
        runtime_config=InferenceRuntimeConfig(
            **inference_sim_task.runtime_config.model_dump()
        )
        repo = ModelConfigRepository(self.repository.session)
        repo.create(model_config_)
        repo = SystemConfigRepository(self.repository.session)
        repo.create(system_config)
        repo = InferenceRuntimeConfigRepository(self.repository.session)
        repo.create(runtime_config)
        entity = InferenceSimTask(
            name=inference_sim_task.name,
            model_config_id=model_config_.id,
            system_config_id=system_config.id,
            runtime_config_id=runtime_config.id,
            model_config_=model_config_,
            system_config=system_config,
            runtime_config=runtime_config
        )
        return super().create(entity)
    
    def run(self, inference_sim_task_id: UUID):
        inference_sim_task : InferenceSimTask = self.repository.get_by_id(inference_sim_task_id)
        if not inference_sim_task:
            raise ValueError(f"inference_sim_task_id {inference_sim_task_id} not found")
        task = run_task.delay(inference_sim_task_id)
        print(task)
        return inference_sim_task
    