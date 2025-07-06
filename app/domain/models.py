from datetime import datetime, timezone
from typing import Dict, Optional, TypeVar
from uuid import UUID, uuid4
from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy import TIMESTAMP
from enum import Enum
from sqlalchemy.dialects.postgresql import JSONB


class BaseSQLModel(SQLModel):
    """基础模型,所有表都应该有这些字段"""
    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        index=True
    )

    # 修改点：使用 Field 的标准参数定义时间字段
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=TIMESTAMP(timezone=True),
        nullable=False
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_type=TIMESTAMP(timezone=True),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)}
    )


# 泛型类型变量，限定必须是BaseSQLModel或其子类
TBaseSQLModel = TypeVar("TSQLModel", bound=BaseSQLModel)

class RoleEnum(str, Enum):
    ADMIN = "admin"
    USER = "user"

class UserBase(BaseSQLModel, table=False):

    username: str = Field(
        unique=True,
        index=True,
        max_length=50
    )
    hashed_password: str
    is_active: bool = Field(default=True)
    role: RoleEnum = Field(default=RoleEnum.USER)

class UserCreate(UserBase):
    """用户创建模型"""



class User(UserBase, table=True):
    """用户模型"""
    __tablename__ = "users"

    # User 和 Config 的对应关系 (一对多)
    # model_configs: list["ModelConfig"] = Relationship(back_populates="user")
    # system_configs: list["SystemConfig"] = Relationship(back_populates="user")
    # inference_runtime_configs: list["InferenceRuntimeConfig"] = Relationship(back_populates="user")
    # train_runtime_configs: List["TrainRuntimeConfig"] = Relationship(
    #     back_populates="user"
    # )

    # # User 和 Task 的对应关 (一对多)
    # inference_sim_tasks: List["InferenceSimTask"] = Relationship(
    #     back_populates="user"
    # )

class ConfigBaseSQLModel(BaseSQLModel, table=False):
    """配置基础模型"""
    # 外键
    # user_id: UUID = Field(
    #     foreign_key="users.id",
    #     description="用户外键"
    # )

    # 字段
    name: str = Field(
        index=True,
        max_length=100,
        unique=True
    )

    is_template: bool = Field(
        default=True,
        description="标识是否为模板配置,没有任务关联的配置为模板配置"
    )

    params: dict = Field(
        default={},
        sa_type=JSONB,  # 指定为 PostgreSQL 的 JSONB 类型
        description="配置参数"
    )


TConfigBaseSQLModel = TypeVar("TConfigBaseSQLModel", bound=ConfigBaseSQLModel)

class ModelConfig(ConfigBaseSQLModel, table=True):
    __tablename__ = "model_configs"

    type: str = Field(max_length=50)

    # 关系
    # user: "User" = Relationship(back_populates="model_configs")

    inference_sim_task: Optional["InferenceSimTask"] = Relationship(
        back_populates="model_config_",
        sa_relationship_kwargs={'uselist': False}
    )

class SystemTypeEnum(str, Enum):
    NPU = "npu"
    GPU = "gpu"


class SystemConfig(ConfigBaseSQLModel, table=True):
    __tablename__ = "system_configs"

    type: SystemTypeEnum

    # 关系
    # user: "User" = Relationship(back_populates="system_configs")

    # 一对一关系 (可空)
    inference_sim_task: Optional["InferenceSimTask"] = Relationship(
        back_populates="system_config",
        sa_relationship_kwargs={"uselist": False}
    )

class InferenceRuntimeConfig(ConfigBaseSQLModel, table=True):
    __tablename__ = "inference_runtime_configs"

    # 关系
    # user: "User" = Relationship(back_populates="inference_runtime_configs")

    # 一对一关系 (可空)
    inference_sim_task: Optional["InferenceSimTask"] = Relationship(
        back_populates="runtime_config",
        sa_relationship_kwargs={"uselist": False}
    )


class SimTaskStatusEnum(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SimTaskBaseSQLModel(BaseSQLModel):
    """任务基础模型"""
    # 外键
    # user_id: UUID = Field(foreign_key="users.id")
    model_config_id: UUID = Field(foreign_key="model_configs.id")
    system_config_id: UUID = Field(foreign_key="system_configs.id")

    name: str = Field(index=True, unique=True, max_length=100)
    status: SimTaskStatusEnum = Field(default=SimTaskStatusEnum.PENDING)
    result: dict = Field(
        default={},
        sa_type=JSONB,
        description="存储结果"
    )


TSimTaskBaseSQLModel = TypeVar("TSimTaskBaseSQLModel", bound=SimTaskBaseSQLModel)

class InferenceSimTask(SimTaskBaseSQLModel, table=True):
    __tablename__ = "inference_sim_tasks"

    # # 关系 - 使用字符串引用
    # user: "User" = Relationship(back_populates="inference_sim_tasks")
    runtime_config_id: UUID = Field(foreign_key="inference_runtime_configs.id")

    model_config_: "ModelConfig" = Relationship(back_populates="inference_sim_task")
    system_config: "SystemConfig" = Relationship(back_populates="inference_sim_task")
    runtime_config: "InferenceRuntimeConfig" = Relationship(back_populates="inference_sim_task")