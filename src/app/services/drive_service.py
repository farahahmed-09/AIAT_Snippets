import os
import requests
import logging
import re
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class DriveService:
    @staticmethod
    def download_video_file(url: str, output_dir: str) -> str:
        """
        Downloads a video file from a URL to the specified output directory.
        Handles Google Drive links and the large file confirmation page.
        """
        try:
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            file_id = None
            if "drive.google.com" in url:
                if "/file/d/" in url:
                    file_id = url.split("/file/d/")[1].split("/")[0]
                elif "id=" in url:
                    from urllib.parse import parse_qs
                    file_id = parse_qs(urlparse(url).query).get(
                        "id", [None])[0]

            if file_id:
                return DriveService._download_from_gdrive(file_id, output_dir)

            # Generic download for non-gdrive links
            path = urlparse(url).path
            file_name = os.path.basename(path)
            if not file_name or "." not in file_name:
                file_name = "downloaded_video.mp4"
            video_path = os.path.join(output_dir, file_name)

            if os.path.exists(video_path) and os.path.getsize(video_path) > 1000:
                logger.info(f"File {video_path} already exists. Skipping.")
                return video_path

            logger.info(f"Downloading {url} to {video_path}...")
            with requests.get(url, stream=True) as r:
                r.raise_for_status()
                with open(video_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=65536):
                        f.write(chunk)
            return video_path

        except Exception as e:
            logger.error(f"Download failed for {url}: {str(e)}", exc_info=True)
            raise Exception(f"Download failed: {str(e)}")

    @staticmethod
    def _download_from_gdrive(file_id: str, output_dir: str) -> str:
        video_path = os.path.join(output_dir, "downloaded_video.mp4")

        # Check if already exists and is not just an HTML error page
        if os.path.exists(video_path) and os.path.getsize(video_path) > 1000000:
            logger.info(
                f"Video {video_path} already exists. Skipping gdrive download.")
            return video_path

        logger.info(f"Downloading from Google Drive ID: {file_id}")
        base_url = "https://drive.google.com/uc?export=download"

        session = requests.Session()
        response = session.get(base_url, params={'id': file_id}, stream=True)
        logger.debug(f"Initial request status: {response.status_code}")

        token = None
        # Try cookie first
        for key, value in response.cookies.items():
            if key.startswith('download_warning'):
                token = value
                break

        # Try finding in HTML if cookie fails
        if not token:
            html_content = response.text
            # Look for name="confirm" value="xxxxx"
            match = re.search(
                r'name="confirm"\s+value="([^"]+)"', html_content)
            if match:
                token = match.group(1)
                logger.debug(f"Found confirmation token in HTML: {token}")
                # Optimization: For direct download without cookies, usercontent domain is more reliable
                base_url = "https://drive.usercontent.google.com/download"

        if token:
            params = {'id': file_id, 'confirm': token, 'export': 'download'}
            response = session.get(base_url, params=params, stream=True)
            logger.debug(
                f"Requested with token, status: {response.status_code}")

        with open(video_path, "wb") as f:
            for chunk in response.iter_content(131072):  # 128KB chunks
                if chunk:
                    f.write(chunk)

        logger.info(
            f"Gdrive Download complete: {video_path} ({os.path.getsize(video_path)} bytes)")
        return video_path
