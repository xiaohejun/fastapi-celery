import time
import celery
from uuid import UUID
from app.worker.celery import app

# class CeleryInferenceSimTask(celery.Task): ...
    # def __init__(self, sim_task_id: UUID):
    #     super().__init__()
    #     self.sim_task_id = sim_task_id
    
    # def run(self):
    #     print("sim_task_id: begin ", self.sim_task_id)
    #     time.sleep(10)
    #     print("sim_task_id: end", self.sim_task_id)

# @app.task(bound=True)
# def run_inference_sim_task(self, sim_task_id: UUID):
#     print("sim_task_id: begin ", sim_task_id)
#     time.sleep(10)
#     print("sim_task_id: end", sim_task_id)

# # 注册Celery任务
# inference_sim_task = app.register_task(
#     CeleryInferenceSimTask(), 
#     name='inference_sim_task'
# )

from celery import Task
from app.worker.celery import app
import logging
# 自定义任务类
class CustomTask(Task):
    # 1. 自动重试配置 (可选)
    autoretry_for = (ConnectionError, TimeoutError)
    max_retries = 3
    retry_backoff = True  # 启用指数退避
    retry_jitter = True   # 添加随机抖动避免惊群

    # 2. 任务执行主逻辑
    # def run(self, *args, **kwargs):
        # 3. 成功回调
    def on_success(self, retval, task_id, args, kwargs):
        self.get_logger().info(
            f"任务 {task_id} 成功! "
            f"结果={retval}, 参数={args}/{kwargs}"
        )

    # 4. 失败回调
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        self.get_logger().error(
            f"任务 {task_id} 失败! "
            f"错误={exc}, 跟踪信息={einfo.traceback}"
        )

    # 5. 日志工具方法
    def get_logger(self):
        logger = logging.getLogger(self.name)
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

@app.task
def run_task(sim_task_id: UUID):
    time.sleep(10)
    return True
