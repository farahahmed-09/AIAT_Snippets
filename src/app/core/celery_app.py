

from celery import Celery
from celery.schedules import crontab
from src.app.core.config import settings

celery_app = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["src.app.workers.tasks"]
)

celery_app.conf.task_routes = {
    "src.app.workers.tasks.process_session_pipeline": "main-queue",
    "src.app.workers.tasks.generate_snippet_video": "video-queue",
}

# Celery Beat Schedule for periodic tasks
celery_app.conf.beat_schedule = {
    'cleanup-ephemeral-snippets': {
        'task': 'src.app.workers.tasks.cleanup_ephemeral_snippets_task',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    'trim-old-source-videos': {
        'task': 'src.app.workers.tasks.trim_old_source_videos_task',
        'schedule': crontab(hour=3, minute=0),  # Daily at 3 AM
    },
}
