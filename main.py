import os
import re
import tempfile
import uuid
import asyncio
import requests
from typing import List, Dict, Optional
from datetime import datetime

import torch
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from funasr import AutoModel
from pydantic import BaseModel
from enum import Enum

app = FastAPI()

# 任务状态枚举
class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

# 任务模型
class ASRTask(BaseModel):
    id: str
    status: TaskStatus
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

# 任务存储（在生产环境中应该使用数据库）
tasks: Dict[str, ASRTask] = {}

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


# 函数，用于从URL下载文件到临时目录
def download_file_from_url(url: str) -> str:
    # 获取文件扩展名
    filename = url.split("/")[-1]
    suffix = os.path.splitext(filename)[1]
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_filename = temp_file.name
        
    # 下载文件
    response = requests.get(url)
    response.raise_for_status()
    
    # 保存文件
    with open(temp_filename, 'wb') as f:
        f.write(response.content)
    
    return temp_filename


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


# 异步处理ASR任务
async def process_asr_task(task_id: str, file_path: str, ext_name: str):
    task = tasks[task_id]
    task.status = TaskStatus.PROCESSING
    task.result = None
    task.error = None
    
    temp_input_file_path = file_path
    try:
        if ext_name not in ['wav', 'mp3']:
            # 如果不是音频文件,用ffmpeg转换为音频文件
            temp_input_file_path = convert_audio(temp_input_file_path)

        print(f"Processing task {task_id} with file {temp_input_file_path}")

        # 运行ASR模型
        result = model.generate(
            input=temp_input_file_path,
            batch_size_s=300,
            batch_size_threshold_s=60,
        )

        try:
            srt = funasr_to_srt(result)
            result[0]['srt'] = srt
        except Exception as e:
            print(f'SRT conversion failed: {e}')

        # 更新任务状态为完成
        task.status = TaskStatus.COMPLETED
        task.result = {"result": result}
        task.completed_at = datetime.now()
    except Exception as e:
        # 更新任务状态为失败
        task.status = TaskStatus.FAILED
        task.error = str(e)
        task.completed_at = datetime.now()
        print(f"Task {task_id} failed: {e}")
    finally:
        # 清理临时文件
        for temp_file in [temp_input_file_path]:
            if temp_file and os.path.exists(temp_file):
                os.remove(temp_file)


@app.post("/asr/task")
async def create_asr_task(file: List[UploadFile] = File(...), background_tasks: BackgroundTasks = None):
    try:
        if not file or any(f.filename == "" for f in file):
            raise Exception("No file was uploaded")
        if len(file) != 1:
            raise Exception("Only one file can be uploaded at a time")
        file = file[0]

        # 创建任务ID
        task_id = str(uuid.uuid4())
        
        # 创建任务对象
        task = ASRTask(
            id=task_id,
            status=TaskStatus.PENDING,
            created_at=datetime.now()
        )
        
        # 保存任务到存储中
        tasks[task_id] = task
        
        # 保存上传的文件
        ext_name = os.path.splitext(file.filename)[1].strip('.')
        temp_input_file_path = await save_upload_file(file)
        
        # 启动后台任务处理ASR
        if background_tasks:
            background_tasks.add_task(process_asr_task, task_id, temp_input_file_path, ext_name)
        else:
            # 如果没有background_tasks，直接运行（用于测试）
            asyncio.create_task(process_asr_task(task_id, temp_input_file_path, ext_name))
        
        return {"task_id": task_id, "status": task.status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/asr/task/{task_id}")
async def get_task_status(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks[task_id]
    return {"task_id": task.id, "status": task.status, "created_at": task.created_at, "completed_at": task.completed_at}


@app.get("/asr/task/{task_id}/result")
async def get_task_result(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks[task_id]
    
    if task.status == TaskStatus.PENDING or task.status == TaskStatus.PROCESSING:
        raise HTTPException(status_code=400, detail=f"Task is not completed yet. Current status: {task.status}")
    
    if task.status == TaskStatus.FAILED:
        raise HTTPException(status_code=500, detail=f"Task failed with error: {task.error}")
    
    return task.result


# 新增的数据模型，用于通过URL创建任务
class ASRTaskURL(BaseModel):
    url: str


@app.post("/asr/task/url")
async def create_asr_task_from_url(task_data: ASRTaskURL, background_tasks: BackgroundTasks = None):
    try:
        url = task_data.url
        if not url:
            raise Exception("URL is required")
        
        # 创建任务ID
        task_id = str(uuid.uuid4())
        
        # 创建任务对象
        task = ASRTask(
            id=task_id,
            status=TaskStatus.PENDING,
            created_at=datetime.now()
        )
        
        # 保存任务到存储中
        tasks[task_id] = task
        
        # 从URL下载文件
        temp_input_file_path = download_file_from_url(url)
        
        # 获取文件扩展名
        filename = url.split("/")[-1]
        ext_name = os.path.splitext(filename)[1].strip('.').lower()
        
        # 启动后台任务处理ASR
        if background_tasks:
            background_tasks.add_task(process_asr_task, task_id, temp_input_file_path, ext_name)
        else:
            # 如果没有background_tasks，直接运行（用于测试）
            asyncio.create_task(process_asr_task(task_id, temp_input_file_path, ext_name))
        
        return {"task_id": task_id, "status": task.status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=12369)  # 运行FastAPI应用
