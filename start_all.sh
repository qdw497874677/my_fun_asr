#!/bin/bash

# 启动FastAPI服务
echo "Starting FastAPI service..."
uvicorn main:app --host 0.0.0.0 --port 12369 &

# 等待几秒钟让FastAPI服务启动
sleep 5

# 启动Gradio服务
echo "Starting Gradio service..."
python gradio_app.py

# 等待任何进程退出
wait
