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

### 方式二：Docker部署

本项目提供两种Docker部署方式：

#### 1. 使用预构建的镜像 (推荐)

这种方式会直接从Docker Hub拉取已经构建好的镜像，简单快捷。

```bash
docker-compose up -d
```
此命令会使用 `docker-compose.yml` 文件。

#### 2. 本地构建镜像

如果您修改了代码 (`main.py`)、依赖 (`requirements.txt`) 或 `Dockerfile`，需要重新在本地构建镜像。这里提供两种方式：

**方法A：使用 `docker` 命令手动构建和运行 (适合初学者)**

1.  **构建镜像**: 在项目根目录运行以下命令，构建一个名为 `my_fun_asr` 的镜像。
    ```bash
    docker build -t my_fun_asr:latest .
    ```

2.  **运行容器**: 使用刚刚构建的镜像来启动一个容器。
    ```bash
    docker run -d -p 12369:12369 --name my_fun_asr_container my_fun_asr:latest
    ```
    - `-d`: 后台运行
    - `-p 12369:12369`: 将主机的12369端口映射到容器的12369端口
    - `--name my_fun_asr_container`: 给容器起一个名字，方便管理

**方法B：使用 `docker-compose` 构建和运行**

```bash
docker-compose -f docker-compose.build.yml up -d --build
```
此命令会使用 `docker-compose.build.yml` 文件来构建并启动服务。`-f` 参数用于指定配置文件，`--build` 标志会强制重新构建镜像。

## 相关接口

### 统一响应格式

所有接口都遵循统一的JSON响应格式，HTTP状态码始终为 `200`。通过业务状态码 `code` 来判断请求结果。

```json
{
  "code": 200, // 业务状态码: 200-成功, 4xx-客户端错误, 5xx-服务端错误
  "message": "Success", // 描述信息
  "data": {} // 响应数据
}
```

### 同步转换接口

- **URL**: `/asr`
- **Method**: `POST`
- **Description**: 直接上传文件进行语音识别，同步返回结果。适用于处理时间较短的音频。
- **Request**: `multipart/form-data`，包含一个名为 `file` 的文件字段。
- **Success Response (`code: 200`)**:
  ```json
  {
    "code": 200,
    "message": "Success",
    "data": {
      "result": [
        // ...识别结果...
      ]
    }
  }
  ```

### 异步转换接口

对于较大的文件或较长的音频，建议使用异步接口，以避免请求超时。

#### 1. 创建转换任务

- **URL**: `/tasks`
- **Method**: `POST`
- **Description**: 创建一个异步语音识别任务。你可以上传本地文件，或者提供一个文件的URL。
- **Success Response (`code: 200`)**:
  ```json
  {
    "code": 200,
    "message": "Task created successfully",
    "data": {
      "task_id": "your-unique-task-id",
      "status": "pending"
    }
  }
  ```

#### 2. 查看所有任务

- **URL**: `/tasks`
- **Method**: `GET`
- **Description**: 获取所有任务的列表及其当前状态。
- **Success Response (`code: 200`)**:
  ```json
  {
    "code": 200,
    "message": "Success",
    "data": {
      "tasks": [
        // ...任务对象列表...
      ]
    }
  }
  ```

#### 3. 查看单个任务状态

- **URL**: `/tasks/{task_id}`
- **Method**: `GET`
- **Description**: 根据任务ID查询任务的当前状态。
- **Success Response (`code: 200`)**:
  ```json
  {
    "code": 200,
    "message": "Success",
    "data": {
      "id": "your-unique-task-id",
      "status": "processing",
      // ...其他任务字段...
    }
  }
  ```
- **Error Response (`code: 404`)**:
  ```json
  {
    "code": 404,
    "message": "Task not found",
    "data": {}
  }
  ```

#### 4. 获取任务结果

- **URL**: `/tasks/{task_id}/result`
- **Method**: `GET`
- **Description**: 如果任务已完成，获取语音识别的结果。
- **Success Response (`code: 200`)**:
  ```json
  {
    "code": 200,
    "message": "Success",
    "data": {
      "result": [
        // ...识别结果...
      ]
    }
  }
  ```
- **Error Responses**:
  - **任务不存在 (`code: 404`)**
  - **任务未完成 (`code: 400`)**
  - **任务失败 (`code: 500`)**
