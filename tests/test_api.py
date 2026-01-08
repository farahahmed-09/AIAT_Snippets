import pytest
from fastapi.testclient import TestClient
from src.app.main import app
import unittest.mock as mock

client = TestClient(app)


def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to AIAT Snippets API"}


def test_get_sessions():
    # Test getting sessions list
    response = client.get("/api/v1/sessions")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@mock.patch("src.services.supabase.SupabaseService.get")
@mock.patch("src.services.supabase.SupabaseService.create")
@mock.patch("src.app.workers.tasks.process_session_pipeline.delay")
def test_upload_session_mocked(mock_delay, mock_create, mock_get):
    # Mock behavior
    mock_get.return_value = None  # No existing session
    mock_create.return_value = {
        "id": 1, "name": "Test", "drive_link": "http://test.com/v"}

    payload = {
        "name": "Test Session",
        "module": "Testing",
        "drive_link": "https://drive.google.com/file/d/15K4mcpxMeHwa2EV_6OtaI8nV7DNOmlXf/view?usp=sharing"
    }

    response = client.post("/api/v1/upload-session", json=payload)

    assert response.status_code == 200
    assert response.json()["id"] == 1
    mock_delay.assert_called_once_with(1)


def test_get_invalid_job_status():
    response = client.get("/api/v1/jobs/999999/status")
    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"
