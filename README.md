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

### 方式二：Docker镜像构建

#### 构建Docker镜像

要构建项目的Docker镜像，可以使用以下命令：

```
docker build -t my_fun_asr .
```

这将基于项目根目录下的Dockerfile构建一个名为`my_fun_asr`的镜像。

#### 使用Docker运行

构建镜像后，可以使用以下命令运行容器：

```
docker run -p 12369:12369 -p 7860:7860 my_fun_asr
```

这将启动容器并将容器的端口12369（FastAPI服务）和7860（Gradio界面）映射到主机的相应端口。

#### 使用Docker Compose运行

项目提供了docker-compose.yml文件，可以更方便地管理多容器应用：

```
docker-compose up -d
```

这将启动两个服务：
1. `app`服务：运行FastAPI应用，提供ASR服务接口
2. `gradio`服务：运行Gradio界面，依赖于app服务

使用以下命令停止服务：

```
docker-compose down
```

#### Docker镜像构建说明

Dockerfile使用Python 3.10 slim镜像作为基础，执行以下步骤：
1. 设置工作目录为`/app`
2. 复制并安装requirements.txt中的依赖项
3. 复制项目文件到容器中
4. 暴露端口12369（FastAPI）和7860（Gradio）
5. 启动FastAPI应用

注意：如果在Apple Silicon Mac上构建镜像，可能需要针对ARM64架构进行特殊处理。

## 相关接口

### 同步接口

提供的接口：`POST` http://127.0.0.1:12369/asr
- 支持mp3、wav音频文件转文字
![](example.jpg)
- 支持mp4等视频文件转文字
![](example2.jpg)

### 异步接口

1. 创建识别任务：`POST` http://127.0.0.1:12369/asr/task
   - 通过上传文件创建一个新的ASR识别任务，返回任务ID和状态
   
2. 通过URL创建识别任务：`POST` http://127.0.0.1:12369/asr/task/url
   - 通过文件URL创建一个新的ASR识别任务，返回任务ID和状态
   - 请求体：`{"url": "文件URL"}`
   
3. 查询任务状态：`GET` http://127.0.0.1:12369/asr/task/{task_id}
   - 查询指定任务的当前状态（pending, processing, completed, failed）
   
4. 获取任务结果：`GET` http://127.0.0.1:12369/asr/task/{task_id}/result
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
