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

### 同步转换接口

- **URL**: `/asr`
- **Method**: `POST`
- **Description**: 直接上传文件进行语音识别，同步返回结果。适用于处理时间较短的音频。
- **Request**: `multipart/form-data`，包含一个名为 `file` 的文件字段。
- **Example**:
  ```bash
  curl -X POST "http://127.0.0.1:12369/asr" -F "file=@/path/to/your/audio.mp3"
  ```
- 支持mp3、wav音频文件转文字
![](example.jpg)
- 支持mp4等视频文件转文字
![](example2.jpg)

### 异步转换接口

对于较大的文件或较长的音频，建议使用异步接口，以避免请求超时。

#### 1. 创建转换任务

- **URL**: `/tasks`
- **Method**: `POST`
- **Description**: 创建一个异步语音识别任务。你可以上传本地文件，或者提供一个文件的URL。
- **Request Body**:
  - `multipart/form-data` with a `file` field (for file uploads).
  - OR `form-data` with a `file_url` field (for URL-based files).
- **Success Response**:
  ```json
  {
    "task_id": "your-unique-task-id",
    "status": "pending"
  }
  ```
- **Example (File Upload)**:
  ```bash
  curl -X POST "http://127.0.0.1:12369/tasks" -F "file=@/path/to/your/audio.mp3"
  ```
- **Example (File URL)**:
  ```bash
  curl -X POST "http://127.0.0.1:12369/tasks" -F "file_url=http://example.com/audio.mp3"
  ```

#### 2. 查看任务状态

- **URL**: `/tasks/{task_id}`
- **Method**: `GET`
- **Description**: 根据任务ID查询任务的当前状态。
- **URL Params**:
  - `task_id` (string, required): The ID of the task.
- **Success Response**:
  ```json
  {
    "task_id": "your-unique-task-id",
    "status": "processing", // or "pending", "completed", "failed"
    "created_at": "2023-10-28T12:00:00.000Z",
    "completed_at": null // or timestamp when completed/failed
  }
  ```
- **Example**:
  ```bash
  curl http://127.0.0.1:12369/tasks/your-unique-task-id
  ```

#### 3. 获取任务结果

- **URL**: `/tasks/{task_id}/result`
- **Method**: `GET`
- **Description**: 如果任务已完成，获取语音识别的结果。
- **URL Params**:
  - `task_id` (string, required): The ID of the task.
- **Success Response**: 返回与同步接口 `/asr` 相同的识别结果JSON。
- **Error Response**:
  - 如果任务尚未完成，返回 `400 Bad Request`。
  - 如果任务失败，返回 `500 Internal Server Error` 并附带错误信息。
- **Example**:
  ```bash
  curl http://127.0.0.1:12369/tasks/your-unique-task-id/result
  ```
