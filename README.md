# 语音转文字ASR工具

基于funasr开源项目和模型，快速搭建语音转文字的api服务

## 安装

### 方式一：本地python环境启动

安装所需软件包

``` 
pip install -i https://mirror.baidu.com/pypi/simple -r requirements.txt
```

启动

``` 
python main.py
```

### 方式二：docker-compose一键安装

```
docker-compose up -d
```

## 相关接口

### 同步接口

提供的接口：`POST` http://127.0.0.1:12369/asr
- 支持mp3、wav音频文件转文字
![](example.jpg)
- 支持mp4等视频文件转文字
![](example2.jpg)

### 异步接口

1. 创建识别任务：`POST` http://127.0.0.1:12369/asr/task
   - 创建一个新的ASR识别任务，返回任务ID和状态
   
2. 查询任务状态：`GET` http://127.0.0.1:12369/asr/task/{task_id}
   - 查询指定任务的当前状态（pending, processing, completed, failed）
   
3. 获取任务结果：`GET` http://127.0.0.1:12369/asr/task/{task_id}/result
   - 获取已完成任务的识别结果

## Gradio界面

项目还提供了一个基于Gradio的Web界面，可以通过以下方式访问：
- 同步识别：直接调用本地模型进行识别
- 异步识别：通过API的异步接口进行识别

启动Gradio界面：
```
python gradio_app.py
```

或者使用start_gradio.sh脚本启动：
```
./start_gradio.sh
```

或者使用Docker-compose启动：
```
docker-compose up -d
```
然后访问 http://127.0.0.1:7860
