from typing import Optional, Any, Dict
from sqlmodel import SQLModel, Field, Session, create_engine, Column
from pydantic import BaseModel
from sqlalchemy import JSON
# 1. 定义自定义 Pydantic 模型
class UserSettings(BaseModel):
    theme: str = "dark"
    notifications: bool = True
    preferences: Dict[str, Any] = {}

# 2. 定义 SQLModel 数据表
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    
    # 数据库存储的字段（JSON字典）
    settings_data: Dict = Field(
        default_factory=dict,
        sa_column=Column(JSON)  # 数据库列类型为JSON
    )
    
    # 3. 定义属性来操作Pydantic模型
    @property
    def settings(self) -> UserSettings:
        """将存储的字典转换为UserSettings模型"""
        return UserSettings.model_validate(self.settings_data)
    
    @settings.setter
    def settings(self, value: UserSettings):
        """将UserSettings模型转换为字典存储"""
        self.settings_data = value.model_dump()

# 初始化数据库
engine = create_engine("sqlite:///example.db")
SQLModel.metadata.create_all(engine)
# 使用示例
with Session(engine) as session:
    # 创建用户
    user = User(
        name="Alice",
        settings=UserSettings(theme="light", preferences={"lang": "en"})
    )
    # 注意：这里我们设置的是settings属性，它会自动更新settings_data
    session.add(user)
    session.commit()
    
    # 查询用户
    db_user = session.get(User, user.id)
    print(db_user.settings)  # 输出: theme='light' notifications=True preferences={'lang': 'en'}
    user_settings = db_user.settings
    print(user_settings.model_dump_json(indent=2))  # <class '__main__.UserSettings'>