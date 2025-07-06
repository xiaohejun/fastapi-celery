# import asyncio
# import json # TODO: 换成其他json库优化性能
# from app.worker import celery_app

# async def task_progress_generator(task_id: str):
#     """生成任务进度事件流"""
#     while True:
#         task = celery_app.AsyncResult(task_id)
        
#         if task.state == 'PENDING':
#             data = {"state": task.state, "progress": 0, "status": "Pending..."}
#         elif task.state == 'PROGRESS':
#             data = {
#                 "state": task.state,
#                 "progress": task.info.get('progress', 0),
#                 "status": task.info.get('status', ''),
#                 "details": task.info
#             }
#         elif task.state == 'SUCCESS':
#             data = {
#                 "state": task.state,
#                 "progress": 100,
#                 "result": task.result,
#                 "status": "Completed!"
#             }
#             yield json.dumps(data)
#             break
#         else:  # FAILURE/REVOKED etc.
#             data = {
#                 "state": task.state,
#                 "progress": task.info.get('progress', 0),
#                 "error": str(task.info),
#                 "status": "Failed"
#             }
#             yield json.dumps(data)
#             break
        
#         yield json.dumps(data)
#         await asyncio.sleep(0.5)  # 更新间隔