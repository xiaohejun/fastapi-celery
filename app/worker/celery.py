from logging import config
import os
import time
# import time

from celery import Celery


from app.core.dependencies import Container
config = Container.config()

app = Celery(
    __name__,
    broker=config["celery"]["broker_url"],
    backend=config["celery"]["result_backend"],
    include=["app.worker.tasks", "app.worker.inference_sim_task"]
)

# """
# task_track_started=True
# 启用任务启动跟踪。当任务开始执行时，状态会变为STARTED（默认只有成功/失败状态）。便于监控长时间运行的任务。

# task_serializer='json'
# 任务序列化格式为JSON。确保任务参数可被序列化后发送到消息队列。

# result_serializer='json'
# 结果序列化格式为JSON。任务返回值会以JSON格式存储在后端。

# accept_content=['json']
# 只接受JSON格式的消息。防止恶意消息注入。

# worker_send_task_events=True
# 允许Worker发送任务事件（如任务开始/成功/失败）。结合监控工具（如Flower）可实现实时任务追踪。

# """
app.conf.update(
    task_track_started=True,
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    worker_send_task_events=True,
)


# @app.task
# def create_task(task_type):
#     time.sleep(int(task_type) * 10)
#     return True

if __name__ == '__main__':
    app.start()
