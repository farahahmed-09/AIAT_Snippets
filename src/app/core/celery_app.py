
from celery import Celery
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
