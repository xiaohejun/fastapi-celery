# 第一阶段：构建阶段
FROM python:3.13 AS builder

# 设置工作目录
WORKDIR /appuser/code

# 复制项目依赖文件
COPY requirements.txt .

RUN pip config set global.index-url http://mirrors.aliyun.com/pypi/simple/ 
RUN pip config set install.trusted-host mirrors.aliyun.com

# 创建虚拟环境并安装依赖
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt

# 第二阶段：运行阶段
FROM python:3.13-slim

# 创建非 root 用户
RUN groupadd -r appgroup && useradd -r -g appgroup -d /app appuser

# 设置工作目录
WORKDIR /appuser/code

# 复制虚拟环境
COPY --from=builder /venv /venv

# 复制项目代码
COPY . .

# 设置环境变量，让系统使用虚拟环境
ENV PATH="/venv/bin:$PATH"

# 更改文件所有权为 appuser
RUN chown -R appuser:appgroup /appuser/code

# 切换到 appuser
USER appuser

# 暴露应用端口
EXPOSE ${API_PORT}

# 启动应用
# CMD ["python", "-m", "app.api.main"]
# CMD ["uvicorn", "app.main:fastapi_app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
# uvicorn app.main:fastapi_app --host ${API_HOST} --port ${API_PORT} --reload