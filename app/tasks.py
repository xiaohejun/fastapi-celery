# from app.worker import celery_app
# import time
# import random

# @celery_app.task(bind=True)
# def long_running_task(self):
#     """模拟长时间运行任务并更新进度"""
#     total_steps = 60
#     self.update_state(
#         state='PROGRESS',
#         meta={'current': 0, 'total': total_steps, 'status': "Starting..."}
#     )
    
#     for step in range(1, total_steps + 1):
#         time.sleep(random.uniform(0.5, 2.0))  # 模拟处理时间
#         progress = int((step / total_steps) * 100)
        
#         self.update_state(
#             state='PROGRESS',
#             meta={
#                 'current': step,
#                 'total': total_steps,
#                 'progress': progress,
#                 'status': f"Processing step {step}/{total_steps}"
#             }
#         )
#     self.update_state(
#         state='SUCCESS',
#         meta={
#             'current': total_steps,
#             'total': total_steps,
#             'progress': 100,
#             'status': f"Processing step {total_steps}/{total_steps}"
#         }
#     ) 
#     return {'result': 'success', 'progress': 100}