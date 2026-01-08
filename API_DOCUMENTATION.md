# AIAT Snippets API Documentation

The AIAT Snippets API provides endpoints for uploading live lecture sessions, monitoring their processing status, retrieving identified snippets, and triggering video generation for specific snippets.

**Base URL**: `http://<server-address>/api/v1`

---

## 1. Sessions Endpoints

### 1.1 Upload Session

Creates a new session record and triggers the background processing pipeline (download, transcription, and AI analysis).

- **Endpoint**: `POST /upload-session`
- **Description**: Accepts a Google Drive link to a lecture video and starts processing.
- **Request Body (JSON)**:
  ```json
  {
    "name": "string",
    "module": "string (optional)",
    "drive_link": "string (Google Drive URL)"
  }
  ```
- **Success Response (200 OK)**:
  ```json
  {
    "id": 1,
    "name": "Lecture 1",
    "module": "Marketing",
    "drive_link": "https://drive.google.com/...",
    "job_status": "Pending",
    "created_at": "2026-01-08T00:00:00Z"
  }
  ```
- **Error Response (400 Bad Request)**:
  - Returns if a session with the same `drive_link` already exists.

### 1.2 List Sessions

Retrieves a list of all sessions with pagination and sorting.

- **Endpoint**: `GET /sessions`
- **Query Parameters**:
  - `skip`: Number of records to skip (default: 0).
  - `limit`: Maximum number of records to return (default: 100).
  - `sort_by`: Field to sort by (default: "created_at").
  - `order`: Sort order ("asc" or "desc", default: "desc").
- **Success Response (200 OK)**:
  ```json
  [
    {
      "id": 1,
      "name": "Lecture 1",
      "job_status": "Finished",
      ...
    }
  ]
  ```

### 1.3 Get Job Status

Checks the current processing status of a session.

- **Endpoint**: `GET /jobs/{session_id}/status`
- **Description**: Rapidly check if a session is "Pending", "Processing", "Finished", or "Failed".
- **Success Response (200 OK)**:
  ```json
  {
    "job_status": "Processing: Analyzing"
  }
  ```

### 1.4 Get Session Results

Retrieves full details of a session, including all identified snippets.

- **Endpoint**: `GET /sessions/{session_id}/results`
- **Success Response (200 OK)**:
  ```json
  {
    "id": 1,
    "name": "Lecture 1",
    "job_status": "Finished",
    "snippets": [
      {
        "id": 101,
        "name": "Marketing Intro",
        "summary": "Introduction to marketing concepts...",
        "start_second": 10,
        "end_second": 250
      }
    ]
  }
  ```

### 1.5 Update Session Plan

Manually update or confirm the snippet selection for a session. This replaces old identified snippets with a new list.

- **Endpoint**: `PATCH /sessions/{session_id}/plan`
- **Request Body (JSON)**:
  ```json
  {
    "snippets": [
      {
        "name": "Custom Snippet Name",
        "start": 120.5,
        "end": 300.2,
        "summary": "Brief summary of the segment"
      }
    ]
  }
  ```
- **Success Response (200 OK)**: Returns the updated session object (similar to 1.4).

---

## 2. Snippets Endpoints

### 2.1 Get Snippet Details

Retrieves details for a specific snippet, including whether it has been processed (indicated by `storage_link`).

- **Endpoint**: `GET /snippets/{snippet_id}`
- **Success Response (200 OK)**:
  ```json
  {
    "id": 101,
    "name": "Marketing Intro",
    "storage_link": "1)_Marketing_Intro.mp4",
    ...
  }
  ```

### 2.2 Process Snippet

Triggers the actual video generation (cropping, styling, adding intro) for a specific snippet.

- **Endpoint**: `POST /snippets/{snippet_id}/process`
- **Description**: Starts the FFmpeg-based worker to generate the final `.mp4` file for the snippet.
- **Success Response (200 OK)**:
  ```json
  {
    "message": "Snippet processing started",
    "task_id": "c62f83de-..."
  }
  ```

### 2.3 Check Processing Task Status

Check the status of a specific snippet generation task using the `task_id` returned by the process endpoint.

- **Endpoint**: `GET /snippets/tasks/{task_id}`
- **Success Response (200 OK)**:
  ```json
  {
    "task_id": "c62f83de-...",
    "status": "SUCCESS",
    "result": "Processed 1 videos."
  }
  ```

### 2.4 Download Snippet

Directly download or stream the generated video file.

- **Endpoint**: `GET /snippets/{snippet_id}/download`
- **Description**: Returns the video file if processing is complete.
- **Success Response**: `video/mp4` file stream.

### 2.5 Static File Access

Alternatively, videos can be accessed directly if the session ID and filename are known.

- **URL Structure**: `GET /output/{session_id}/snippets/{filename}`
- **Example**: `http://api.aiat.com/output/35/snippets/1)_Marketing_Intro.mp4`

---

## 3. Data Schemas

### Session Statuses

- `Pending`: Initial state after upload.
- `Processing: Downloading`: Downloading video from Drive.
- `Processing: Transcribing`: Extracting audio and running Whisper.
- `Processing: Analyzing`: AI identifies meaningful segments.
- `Finished`: Successfully completed.
- `Failed`: An error occurred (error message is usually saved in the database record).

### Snippet Object

```json
{
  "id": "integer",
  "session_id": "integer",
  "name": "string",
  "summary": "string",
  "start_second": "integer",
  "end_second": "integer",
  "created_at": "datetime"
}
```
