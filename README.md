# SmartCut AI Production System

This project automates the creation of video snippets from long-form content using AI. It provides a production-ready API for uploading sessions, processing them with AI agents, and generating styled video clips, with all metadata managed via **Supabase**.

## Features

- **Live Session Upload**: Download videos directly from Google Drive.
- **AI Processing Pipeline**:
  - Parallelized Transcription (Whisper).
  - Intelligent Segmentation & Analysis (CrewAI/LLM).
  - Concept Extraction.
- **Video Generation**:
  - Automated video trimming using FFmpeg.
  - UI Attachment (Intros, Backgrounds).
- **Job Management**: Asynchronous background processing using Celery & Redis.
- **Supabase Integration**: Real-time database management for sessions and snippets.

## Prerequisites

- **Python 3.10+**
- **Redis** (for Celery broker)
- **FFmpeg** (installed on system path)
- **Supabase Project** (Database and Storage)

## Architecture

The project is structured as a modular FastAPI application:

- `src/app/api`: REST API endpoints (Supabase-backed).
- `src/app/core`: Project configuration and Celery setup.
- `src/app/services`: Business logic (Drive, Transcription, AI Processing, Video manipulation).
- `src/app/workers`: Celery tasks for background processing.
- `src/services/supabase.py`: Unified Supabase client and CRUD operations.

## Installation

1.  **Activate Environment**:

    ```bash
    conda activate aiat
    ```

2.  **Install Dependencies**:

    ```bash
    pip install fastapi uvicorn celery redis supabase pydantic-settings moviepy openai crewai
    ```

3.  **Environment Variables**:
    Create a `.env` file in the root directory:
    ```env
    OPENAI_API_KEY=sk-...
    GEMINI_API_KEY=...
    SUPABASE_URL=https://your-project.supabase.co
    SUPABASE_KEY=your-service-role-key
    SUPABASE_BUCKET=snippets
    CELERY_BROKER_URL=redis://localhost:6379/0
    CELERY_RESULT_BACKEND=redis://localhost:6379/0
    ```

## Running the Application

### 1. Start Redis

Ensure your Redis server is running (standard port 6379).

### 2. Start Celery Worker

This handles heavy background tasks (transcription, AI analysis, video rendering).

```bash
# From the project root
conda run -n snippets celery -A src.app.core.celery_app worker --loglevel=info -Q main-queue,video-queue
```

### 3. Start API Server

```bash
# From the project root
conda run -n snippets uvicorn src.app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Documentation

Once the server is running, visit:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Core Workflows

1.  **Upload & Process**: `POST /api/v1/upload-session` with a drive link.
2.  **Monitor**: `GET /api/v1/jobs/{session_id}/status` to check progress.
3.  **Review Results**: `GET /api/v1/sessions/{session_id}/results` to see identified clips.
4.  **Edit Snippets**: `PATCH /api/v1/sessions/{session_id}/plan` to adjust cut times or logic.
5.  **Generate Video**: `POST /api/v1/snippets/{snippet_id}/process` to render and style a specific clip.
