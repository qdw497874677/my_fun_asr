
FROM python:3.10-slim

# 安装系统级依赖
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt requirements.txt

# 升级pip并安装依赖项
RUN pip install --upgrade pip && pip install -r requirements.txt

# 复制当前目录中的文件到工作目录中
COPY . .

# 暴露端口
EXPOSE 12369
EXPOSE 7860

# 启动 FastAPI 和 Gradio 应用程序
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port 12369 & python gradio_app.py"]
