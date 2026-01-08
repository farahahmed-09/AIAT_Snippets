import pytest
import os
import shutil
from src.app.services.drive_service import DriveService
from src.app.core.config import settings


@pytest.fixture
def temp_test_dir():
    test_dir = os.path.join(settings.TEMP_DIR, "test_download")
    os.makedirs(test_dir, exist_ok=True)
    # yield test_dir
    # if os.path.exists(test_dir):
    #     shutil.rmtree(test_dir)
    yield test_dir


def test_download_mocked(temp_test_dir, requests_mock):
    # Use a subdirectory to avoid collision with real download test
    sub_dir = os.path.join(temp_test_dir, "mocked")
    os.makedirs(sub_dir, exist_ok=True)

    # Mocking the download
    gdrive_url = "https://drive.google.com/file/d/15K4mcpxMeHwa2EV_6OtaI8nV7DNOmlXf/view?usp=sharing"
    direct_url = "https://drive.google.com/uc?export=download&id=15K4mcpxMeHwa2EV_6OtaI8nV7DNOmlXf"

    requests_mock.get(direct_url, content=b"fake video content")

    output_path = DriveService.download_video_file(gdrive_url, sub_dir)

    assert os.path.exists(output_path)
    assert output_path.endswith("downloaded_video.mp4")
    with open(output_path, "rb") as f:
        assert f.read() == b"fake video content"


def test_download_real_case(temp_test_dir):
    # Use a subdirectory to avoid collision with mocked test
    sub_dir = os.path.join(temp_test_dir, "real")
    os.makedirs(sub_dir, exist_ok=True)

    gdrive_url = "https://drive.google.com/file/d/15K4mcpxMeHwa2EV_6OtaI8nV7DNOmlXf/view?usp=sharing"

    try:
        output_path = DriveService.download_video_file(gdrive_url, sub_dir)
        assert os.path.exists(output_path)
        # Check that a multi-MB file was created (real video is ~10MB)
        print("OUTPUT PATH: ", output_path)
        file_size = os.path.getsize(output_path)
        print(f"REAL DOWNLOAD SIZE: {file_size} bytes")
        assert file_size > 1000000
    except Exception as e:
        pytest.fail(f"Download failed unexpectedly: {e}")
