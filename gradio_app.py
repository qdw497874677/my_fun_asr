import gradio as gr
import os
import tempfile
import requests
import time
import json
from main import model, convert_audio, funasr_to_srt, format_timestamp

# FastAPI服务的URL
API_URL = "http://localhost:12369"

def asr_interface_sync(audio_file):
    """
    同步ASR处理函数，用于Gradio界面
    :param audio_file: 上传的音频文件
    :return: 识别结果和SRT字幕
    """
    if audio_file is None:
        return "请上传音频文件", ""
    
    try:
        # 获取上传文件的路径
        input_file_path = audio_file
    
        # 获取文件扩展名
        ext_name = os.path.splitext(input_file_path)[1].strip('.').lower()
        
        # 如果不是wav或mp3格式，需要转换
        if ext_name not in ['wav', 'mp3']:
            input_file_path = convert_audio(input_file_path)
        
        # 使用funasr模型进行语音识别
        result = model.generate(
            input=input_file_path,
            batch_size_s=300,
            batch_size_threshold_s=60,
        )
        
        # 获取识别文本
        text_result = result[0]['text']
        
        # 生成SRT字幕
        try:
            srt_result = funasr_to_srt(result)
        except Exception as e:
            srt_result = f"生成SRT字幕时出错: {str(e)}"
        
        # 清理临时文件
        if ext_name not in ['wav', 'mp3'] and os.path.exists(input_file_path):
            os.remove(input_file_path)
            
        return text_result, srt_result
    
    except Exception as e:
        return f"处理过程中出错: {str(e)}", ""

def asr_interface_async(audio_file):
    """
    异步ASR处理函数，用于Gradio界面
    :param audio_file: 上传的音频文件
    :return: 识别结果和SRT字幕
    """
    if audio_file is None:
        return "请上传音频文件", ""
    
    try:
        # 创建任务
        with open(audio_file, 'rb') as f:
            files = {'file': (os.path.basename(audio_file), f, 'audio/wav')}
            response = requests.post(f"{API_URL}/asr/task", files=files)
        
        if response.status_code != 200:
            return f"创建任务失败: {response.text}", ""
        
        task_data = response.json()
        task_id = task_data["task_id"]
        
        # 轮询任务状态
        status_output = f"任务ID: {task_id}\n状态: {task_data['status']}\n"
        status_output += "正在处理中，请稍候..."
        
        # 等待任务完成
        while True:
            # 获取任务状态
            status_response = requests.get(f"{API_URL}/asr/task/{task_id}")
            if status_response.status_code != 200:
                return f"获取任务状态失败: {status_response.text}", ""
            
            status_data = status_response.json()
            current_status = status_data["status"]
            
            if current_status == "completed":
                # 获取任务结果
                result_response = requests.get(f"{API_URL}/asr/task/{task_id}/result")
                if result_response.status_code != 200:
                    return f"获取任务结果失败: {result_response.text}", ""
                
                result_data = result_response.json()
                result = result_data["result"]
                
                # 获取识别文本
                text_result = result[0]['text']
                
                # 生成SRT字幕
                try:
                    srt_result = funasr_to_srt(result)
                except Exception as e:
                    srt_result = f"生成SRT字幕时出错: {str(e)}"
                
                return text_result, srt_result
            elif current_status == "failed":
                return f"任务处理失败", ""
            
            # 等待一段时间后再次检查
            time.sleep(1)
    
    except Exception as e:
        return f"处理过程中出错: {str(e)}", ""

# 创建Gradio界面
with gr.Blocks(title="语音识别工具") as demo:
    gr.Markdown("# 语音识别工具")
    gr.Markdown("上传音频文件进行语音识别，支持wav、mp3等格式")
    
    with gr.Row():
        with gr.Column():
            audio_input = gr.Audio(
                label="上传音频文件",
                type="filepath"
            )
            with gr.Row():
                sync_btn = gr.Button("同步识别")
                async_btn = gr.Button("异步识别")
        
        with gr.Column():
            text_output = gr.Textbox(
                label="识别结果",
                lines=10,
                interactive=False
            )
            srt_output = gr.Textbox(
                label="SRT字幕",
                lines=10,
                interactive=False
            )
    
    # 设置按钮点击事件
    sync_btn.click(
        fn=asr_interface_sync,
        inputs=audio_input,
        outputs=[text_output, srt_output]
    )
    
    async_btn.click(
        fn=asr_interface_async,
        inputs=audio_input,
        outputs=[text_output, srt_output]
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
