import gradio as gr
from main import model, funasr_to_srt, convert_audio
import os
import tempfile

def transcribe_audio(audio_file):
    if audio_file is None:
        return "Please upload an audio file.", ""

    temp_input_file_path = None
    try:
        # Save the uploaded audio to a temporary file
        suffix = os.path.splitext(audio_file.name)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(audio_file.read())
            temp_input_file_path = temp_file.name

        # Convert audio if necessary
        ext_name = os.path.splitext(temp_input_file_path)[1].strip('.')
        if ext_name not in ['wav', 'mp3']:
            temp_input_file_path = convert_audio(temp_input_file_path)

        # Perform ASR
        result = model.generate(
            input=temp_input_file_path,
            batch_size_s=300,
            batch_size_threshold_s=60,
        )

        # Extract text and generate SRT
        text_result = result[0]['text']
        srt_result = funasr_to_srt(result)

        return text_result, srt_result
    except Exception as e:
        return f"An error occurred: {str(e)}", ""
    finally:
        if temp_input_file_path and os.path.exists(temp_input_file_path):
            os.remove(temp_input_file_path)

def create_gradio_app():
    with gr.Blocks() as demo:
        gr.Markdown("## FunASR Audio Transcription")
        with gr.Row():
            audio_input = gr.File(label="Upload Audio File")
        with gr.Row():
            transcription_output = gr.Textbox(label="Transcription")
        with gr.Row():
            srt_output = gr.Textbox(label="SRT Subtitles")
        
        audio_input.change(
            fn=transcribe_audio,
            inputs=audio_input,
            outputs=[transcription_output, srt_output]
        )
    return demo

if __name__ == "__main__":
    app = create_gradio_app()
    app.launch()
