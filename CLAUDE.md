# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a speech-to-text ASR (Automatic Speech Recognition) service built on the funasr open-source project. It provides both synchronous and asynchronous APIs for audio transcription, along with a Gradio web interface for interactive usage.

## Architecture

1. **Main Service (`main.py`)**:
   - Built with FastAPI
   - Uses funasr for ASR with paraformer-zh model, fsmn-vad for voice activity detection, and ct-punc for punctuation
   - Supports both CPU and CUDA devices
   - Provides RESTful APIs for:
     - Synchronous transcription (`/asr`)
     - Asynchronous task management (`/tasks`)
   - Integrates a Gradio interface for web-based interaction

2. **Task Management**:
   - In-memory storage for tasks
   - Background processing using FastAPI's BackgroundTasks
   - Task lifecycle: pending → processing → completed/failed
   - Supports both file upload and URL-based file processing

3. **Audio Processing**:
   - Handles multiple audio formats (wav, mp3)
   - Uses ffmpeg for format conversion when needed
   - Generates SRT subtitles from transcription results

4. **Frontend (`gradio_app.py`)**:
   - Simple web interface for uploading audio files and getting transcriptions
   - Built with Gradio

## Common Development Commands

### Running the Service

1. **Local Development**:
   ```bash
   pip install -r requirements.txt
   python main.py
   ```

2. **Docker Deployment**:
   - Using pre-built image:
     ```bash
     docker-compose up -d
     ```
   - Building locally:
     ```bash
     docker-compose -f docker-compose.build.yml up -d --build
     ```

### Dependencies

Main dependencies include:
- FastAPI for the web framework
- funasr for speech recognition
- PyTorch for model inference
- ffmpeg for audio processing
- Gradio for the web interface

## API Endpoints

1. **Synchronous ASR**: `POST /asr` - Direct file upload for immediate transcription
2. **Task Creation**: `POST /tasks` - Create asynchronous transcription task
3. **Task List**: `GET /tasks` - Retrieve all tasks
4. **Task Status**: `GET /tasks/{task_id}` - Get specific task status
5. **Task Result**: `GET /tasks/{task_id}/result` - Get transcription result for completed task
6. **Gradio Interface**: `/gradio` - Web UI for transcription

All APIs follow a unified JSON response format with business status codes.