# 🚀 SmartCut AI - Future Feature Roadmap

This document outlines potential features and enhancements for the SmartCut AI platform, categorized by domain.

---

## 🎨 UI & UX Enhancements

### 1. Advanced Timeline Editor

- **Real Waveform Visualization**: Replace the current randomized waveform with actual audio data from the uploaded video.
- **Keyboard Shortcuts**:
  - `Space`: Play/Pause
  - `J/K/L`: Seek backward/Pause/Seek forward
  - `I/O`: Set In/Out points for the active segment
  - `Del`: Delete selected segment
- **Multi-Segment Selection**: Shift-click or drag-select to move or delete multiple segments at once.
- **Zoom-to-Cursor**: Improve timeline zooming to center on the playhead or mouse cursor.

### 2. Branding & Preview

- **Intro Video Preview**: Add a "Play" button on intro thumbnails in the management dialog to preview the video before selecting/uploading.
- **Live Render Preview**: A low-resolution "draft" render preview that shows the intro and main content transition in real-time.
- **Customizable Lower Thirds**: UI to enter speaker name/title that overlays on the video during the first few seconds.

### 3. Dashboard & Organization

- **Folders/Workspaces**: Group sessions by course, project, or department.
- **Search & Filters**: Search sessions by name, module, or status.
- **Global Progress Center**: A floating panel showing all active background tasks (transcriptions, renders) across all sessions.

---

## ⚙️ Backend & AI Capabilities

### 1. Expanded Input Sources

- **Local File Upload**: Support direct `multipart/form-data` uploads for users who don't use Google Drive.
- **YouTube/Vimeo Integration**: Paste a URL to fetch and process public videos.
- **Dropbox/OneDrive Sync**: Connect other cloud storage providers.

### 2. Advanced AI Analysis

- **Speaker Diarization**: Automatically identify different speakers and label segments accordingly.
- **Automatic Chaptering**: Use LLMs to suggest logical "Chapters" for long lectures.
- **Sentiment & Engagement Analysis**: Highlight parts of the lecture where the speaker is most energetic or where key concepts are explained.
- **Auto-Subtitles**: Generate `.srt` or `.vtt` files and burn them into the video (Hardsubs) or provide them as sidecar files.

### 3. Rendering Engine Upgrades

- **Resolution Options**: Choose between 720p, 1080p, or 4K export.
- **Aspect Ratio Conversion**: "Smart Crop" to convert 16:9 lectures into 9:16 vertical videos for TikTok/Reels/Shorts.
- **Watermarking**: Automatically apply a company/university logo to the corner of every snippet.
- **Outro Support**: Add a customizable outro video/call-to-action at the end of snippets.

---

## 👤 New User Stories

- **The Social Media Manager**: "I want to select a 60-second highlight and have the AI automatically crop it to vertical format so I can post it to Instagram immediately."
- **The Student**: "I want to search for a specific keyword (e.g., 'Photosynthesis') across all my sessions and find the exact snippets where it was discussed."
- **The Admin**: "I want to set a default branding package (Intro/Outro/Logo) for my entire organization so all users stay on-brand."
- **The Collaborator**: "I want to share a session link with a colleague so they can review my trims before I trigger the final render."

---

## 🛠️ Infrastructure & DevOps

- **User Authentication**: Full login system with Role-Based Access Control (RBAC).
- **Webhooks**: Notify external systems (like an LMS or Slack) when a video generation is complete.
- **Usage Analytics**: Track how many minutes of video are processed and rendered per user.
- **S3-Compatible Storage**: Support for AWS S3, DigitalOcean Spaces, or local MinIO for self-hosted deployments.
- **GPU Acceleration**: Optimize Celery workers to use NVIDIA GPUs for faster FFmpeg rendering.

---

## 📈 Marketing & Integration

- **Direct LMS Export**: One-click export to Moodle, Canvas, or Blackboard.
- **Social Media Auto-Post**: Connect to YouTube/LinkedIn API to publish snippets directly.
- **Email Notifications**: Send an email with download links once a batch generation is finished.
