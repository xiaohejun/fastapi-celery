import time
from fastapi import FastAPI, Request

def register_middleware(app: FastAPI):
    async def add_process_time_header(request: Request, call_next):
        start_time = time.perf_counter()
        response = await call_next(request)
        process_time = time.perf_counter() - start_time

        # 根据处理时间的大小选择合适的单位
        if process_time < 1e-3:
            display_time = f"{process_time * 1e6:.2f} μs"
        elif process_time < 1:
            display_time = f"{process_time * 1e3:.2f} ms"
        else:
            display_time = f"{process_time:.2f} s"

        response.headers["X-Process-Time"] = str(process_time)
        print(f"Process time: {display_time}")
        return response

    app.middleware("http")(add_process_time_header)
