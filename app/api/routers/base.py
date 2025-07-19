from typing import Type
from fastapi import APIRouter, Depends
from uuid import UUID
from app.api.dependencies import get_service

from app.services.base import TBaseService

class BaseApiRouter:
    prefix: str
    tags: list[str]

    service_cls: Type[TBaseService]
    create_schema_cls = None
    public_schema_cls = None

    def __init__(self):
        self.router = APIRouter(prefix=self.prefix, tags=self.tags)
        create_schema_cls = self.create_schema_cls
        public_schema_cls = self.public_schema_cls
        service_cls = self.service_cls

        @self.router.post("/create")
        def create(create_data: create_schema_cls, service: service_cls = get_service(self.service_cls)):
            return service.create(create_data)
        
        @self.router.post("/run/{sim_task_id}")
        def run(sim_task_id: UUID, service: service_cls = get_service(self.service_cls)):
            return service.run(sim_task_id)

