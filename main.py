import os
import re
import tempfile
import uuid
import requests
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
from enum import Enum

import torch
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from funasr import AutoModel
from pydantic import BaseModel
import asyncio

app = FastAPI()

# 定义北京时区
beijing_tz = timezone(timedelta(hours=8))

# 任务状态枚举
class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

# 任务模型
class Task(BaseModel):
    id: str
    status: TaskStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[dict] = None
    error: Optional[str] = None

# 任务创建请求模型
class TaskCreateRequest(BaseModel):
    file_url: Optional[str] = None

# 任务存储（内存存储）
tasks_storage = {}


# 从URL下载文件
def download_file_from_url(url: str) -> str:
    response = requests.get(url)
    response.raise_for_status()
    
    # 获取文件名
    parsed_url = urlparse(url)
    file_name = os.path.basename(parsed_url.path)
    if not file_name:
        file_name = f"downloaded_file_{uuid.uuid4().hex[:8]}"
    
    # 保存文件到临时目录
    suffix = os.path.splitext(file_name)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(response.content)
        return temp_file.name


# 运行模型推理的同步函数
def run_model_generate(input_path):
    return model.generate(
        input=input_path,
        batch_size_s=300,
        batch_size_threshold_s=60,
    )

# 异步任务处理函数
async def process_asr_task(task_id: str, file_path: str, is_temp_file: bool = False):
    # 更新任务状态为处理中
    tasks_storage[task_id].status = TaskStatus.PROCESSING
    
    temp_input_file_path = None
    loop = asyncio.get_event_loop()
    try:
        # 如果不是wav或mp3格式，需要转换
        ext_name = os.path.splitext(file_path)[1].strip('.')
        temp_input_file_path = file_path
        if ext_name not in ['wav', 'mp3']:
            # 如果不是音频文件,用ffmpeg转换为音频文件
            temp_input_file_path = await loop.run_in_executor(
                None, convert_audio, temp_input_file_path
            )
        
        # 在线程池中执行语音识别
        result = await loop.run_in_executor(
            None, run_model_generate, temp_input_file_path
        )
        
        # 生成SRT字幕
        try:
            srt = funasr_to_srt(result)
            result[0]['srt'] = srt
        except Exception as e:
            print(f'srt convert fail: {e}')
        
        # 更新任务状态为完成
        tasks_storage[task_id].status = TaskStatus.COMPLETED
        tasks_storage[task_id].completed_at = datetime.now(beijing_tz)
        tasks_storage[task_id].result = {"result": result}
    except Exception as e:
        # 更新任务状态为失败
        tasks_storage[task_id].status = TaskStatus.FAILED
        tasks_storage[task_id].completed_at = datetime.now(beijing_tz)
        tasks_storage[task_id].error = str(e)
    finally:
        # 清理临时文件
        for temp_file in [temp_input_file_path]:
            if temp_file and is_temp_file and os.path.exists(temp_file):
                os.remove(temp_file)


device = "cuda" if torch.cuda.is_available() else "cpu"

model = AutoModel(
    model="paraformer-zh",
    vad_model="fsmn-vad",
    vad_kwargs={"max_single_segment_time": 60000},
    punc_model="ct-punc",
    device=device,
    # spk_model="cam++",
)


def convert_audio(input_file):
    import ffmpeg

    output_file = input_file + ".wav"
    (
        ffmpeg.input(input_file)
        .output(output_file)
        .run(quiet=True)
    )
    return output_file


# 异步函数，用于保存上传的文件到临时目录
async def save_upload_file(upload_file: UploadFile) -> str:
    suffix = os.path.splitext(upload_file.filename)[1]  # 获取文件后缀名
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:  # 创建临时文件
        temp_file.write(await upload_file.read())  # 将上传的文件内容写入临时文件
        return temp_file.name  # 返回临时文件路径


def funasr_to_srt(funasr_result):
    data = funasr_result
    text = data[0]['text']
    timestamps = data[0]['timestamp']

    # 配置参数
    max_chars_per_line = 20  # 每行字幕的最大字符数

    # 首先按照标点符号分割文本为短句
    sentence_pattern = r'([^，。！？,.!?;；、]+[，。！？,.!?;；、]+)'
    phrases = re.findall(sentence_pattern, text)

    # 如果没有找到短句，就把整个文本作为一个短句
    if not phrases:
        phrases = [text]

    # 确保所有文本都被包含
    remaining_text = text
    for phrase in phrases:
        remaining_text = remaining_text.replace(phrase, '', 1)
    if remaining_text.strip():
        phrases.append(remaining_text.strip())

    # 计算每个短句对应的时间戳
    phrase_timestamps = []
    total_chars = len(text)

    char_index = 0
    for phrase in phrases:
        if not phrase.strip():
            continue

        phrase_len = len(phrase)
        # 计算短句在整个文本中的比例
        start_ratio = char_index / total_chars
        end_ratio = (char_index + phrase_len) / total_chars

        start_idx = min(int(start_ratio * len(timestamps)), len(timestamps) - 1)
        end_idx = min(int(end_ratio * len(timestamps)), len(timestamps) - 1)

        if start_idx == end_idx:
            if end_idx < len(timestamps) - 1:
                end_idx += 1

        start_time = timestamps[start_idx][0]
        end_time = timestamps[end_idx][1]

        phrase_timestamps.append((phrase, start_time, end_time))
        char_index += phrase_len

    # 合并短句为合适长度的字幕段落，只考虑字数限制
    text_segments = []
    current_text = ""
    current_start = None
    current_end = None

    for phrase, start, end in phrase_timestamps:
        # 如果当前段落为空，直接添加
        if not current_text:
            current_text = phrase
            current_start = start
            current_end = end
            continue

        # 检查添加当前短句后是否会超出字数限制
        combined_text = current_text + phrase

        if len(combined_text) > max_chars_per_line:
            # 如果会超出限制，保存当前段落并开始新段落
            text_segments.append((current_text, current_start, current_end))
            current_text = phrase
            current_start = start
            current_end = end
        else:
            # 否则合并短句
            current_text = combined_text
            current_end = end

    # 添加最后一个段落
    if current_text:
        text_segments.append((current_text, current_start, current_end))

    # 生成SRT格式，去除每段末尾的标点符号
    srt = ""
    for i, (text, start, end) in enumerate(text_segments, 1):
        # 去除段落末尾的标点符号
        cleaned_text = re.sub(r'[，。！？,.!?;；、]+$', '', text)

        srt += f"{i}\n"
        srt += f"{format_timestamp(start)} --> {format_timestamp(end)}\n"
        srt += f"{cleaned_text.strip()}\n\n"

    return srt


def format_timestamp(milliseconds):
    # 将毫秒转换为SRT格式的时间戳
    seconds, milliseconds = divmod(milliseconds, 1000)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


@app.post("/asr")
async def asr(file: List[UploadFile] = File(...)):
    temp_input_file_path = None
    try:
        if not file or any(f.filename == "" for f in file):
            raise Exception("No file was uploaded")
        if len(file) != 1:
            raise Exception("Only one file can be uploaded at a time")
        file = file[0]

        ext_name = os.path.splitext(file.filename)[1].strip('.')

        temp_input_file_path = await save_upload_file(file)  # 保存上传的文件
        if ext_name not in ['wav', 'mp3']:
            # 如果不是音频文件,用ffmpeg转换为音频文件
            temp_input_file_path = convert_audio(temp_input_file_path)
            # raise Exception("Unsupported file extension")

        print(temp_input_file_path)

        result = model.generate(
            input=temp_input_file_path,
            batch_size_s=300,
            batch_size_threshold_s=60,
            # hotword='魔搭'
        )

        try:
            srt = funasr_to_srt(result)
            result[0]['srt'] = srt
        except:
            print('srt convert fail')

        return {"result": result}  # 返回识别结果
    except Exception as e:  # 捕获其他异常
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # 清理临时文件
        for temp_file in [temp_input_file_path]:
            if temp_file and os.path.exists(temp_file):  # 检查路径是否存在
                os.remove(temp_file)  # 删除文件


# 创建转换任务接口
@app.post("/tasks")
async def create_task(
    background_tasks: BackgroundTasks,
    file: Optional[UploadFile] = File(None),
    file_url: Optional[str] = None
):
    # 检查参数
    if not file and not file_url:
        raise HTTPException(status_code=400, detail="Either file or file_url must be provided")
    
    if file and file_url:
        raise HTTPException(status_code=400, detail="Only one of file or file_url can be provided")
    
    # 创建任务
    task_id = str(uuid.uuid4())
    task = Task(
        id=task_id,
        status=TaskStatus.PENDING,
        created_at=datetime.now(beijing_tz)
    )
    tasks_storage[task_id] = task
    
    # 处理文件
    file_path = None
    is_temp_file = False
    
    try:
        if file:
            # 保存上传的文件
            file_path = await save_upload_file(file)
            is_temp_file = True
        elif file_url:
            # 从URL下载文件
            file_path = download_file_from_url(file_url)
            is_temp_file = True
        
        # 后台处理任务
        background_tasks.add_task(process_asr_task, task_id, file_path, is_temp_file)
        
        return {"task_id": task_id, "status": task.status}
    except Exception as e:
        # 如果创建任务失败，更新任务状态
        task.status = TaskStatus.FAILED
        task.completed_at = datetime.now(beijing_tz)
        task.error = str(e)
        tasks_storage[task_id] = task
        raise HTTPException(status_code=500, detail=str(e))


# 查看任务执行状态接口
@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    if task_id not in tasks_storage:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks_storage[task_id]
    return {
        "task_id": task.id,
        "status": task.status,
        "created_at": task.created_at,
        "completed_at": task.completed_at
    }


# 获取任务执行结果接口
@app.get("/tasks/{task_id}/result")
async def get_task_result(task_id: str):
    if task_id not in tasks_storage:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks_storage[task_id]
    
    if task.status == TaskStatus.PENDING or task.status == TaskStatus.PROCESSING:
        raise HTTPException(status_code=400, detail=f"Task is not completed yet. Current status: {task.status}")
    
    if task.status == TaskStatus.FAILED:
        raise HTTPException(status_code=500, detail=f"Task failed with error: {task.error}")
    
    return task.result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=12369)  # 运行FastAPI应用
