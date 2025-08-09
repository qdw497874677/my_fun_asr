
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt requirements.txt

# 安装 Python 依赖项
RUN pip install --no-cache-dir -r requirements.txt && pip install gradio

# 复制当前目录中的文件到工作目录中
COPY . .

# 暴露端口
EXPOSE 12369
EXPOSE 7860

# 启动 FastAPI 应用程序
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "12369"]
