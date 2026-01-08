import requests
import time
import sys
import os
import argparse

print("DEBUG: Script started at top level")

# Configuration
BASE_URL = "http://localhost:8000/api/v1"


def wait_for_job(session_id, timeout_minutes=30):
    print(f"\n[Monitor] Monitoring progress for Session ID: {session_id}...")
    start_time = time.time()
    last_status = None

    while (time.time() - start_time) < (timeout_minutes * 60):
        try:
            resp = requests.get(f"{BASE_URL}/jobs/{session_id}/status")
            resp.raise_for_status()
            status = resp.json().get("job_status")

            if status != last_status:
                print(f"[{time.strftime('%H:%M:%S')}] Status: {status}")
                last_status = status

            if "Finished" in status:
                return True
            if "Failed" in status:
                print(f"!! Job Failed: {status}")
                return False

        except Exception as e:
            print(f"Error polling status: {e}")

        time.sleep(15)

    print(f"!! Timeout reached after {timeout_minutes} minutes.")
    return False


def test_full_flow(drive_link, session_name="E2E Integration Test"):
    print("==================================================")
    print("      AIAT SNIPPETS - E2E INTEGRATION TEST      ")
    print("==================================================")

    # 1. Upload
    print(f"\n[Step 1] Creating new session...")
    payload = {
        "name": session_name,
        "module": "Integration Testing",
        "drive_link": drive_link
    }

    try:
        resp = requests.post(f"{BASE_URL}/upload-session", json=payload)
        if resp.status_code == 400:
            print(
                "Note: Session with this link already exists. Fetching existing session...")
            # Fetch the existing session by drive link
            sessions_resp = requests.get(f"{BASE_URL}/sessions")
            sessions_resp.raise_for_status()
            existing_session = next(
                (s for s in sessions_resp.json() if s['drive_link'] == drive_link), None)
            if existing_session:
                session_id = existing_session['id']
                print(f"Success: Found existing session {session_id}.")
            else:
                print("!! Could not find the existing session in the list.")
                return
        else:
            resp.raise_for_status()
            session = resp.json()
            session_id = session['id']
            print(f"Success: Session {session_id} created.")
    except Exception as e:
        print(f"Failed to create/fetch session: {e}")
        return

    # 2. Wait for Pipeline
    print(f"DEBUG: Starting wait_for_job for session {session_id}")
    if not wait_for_job(session_id):
        return

    # 3. Check identified snippets
    print(f"\n[Step 2] Retrieving identified snippets...")
    try:
        resp = requests.get(f"{BASE_URL}/sessions/{session_id}/results")
        resp.raise_for_status()
        results = resp.json()
        snippets = results.get("snippets", [])
        print(f"Success: Found {len(snippets)} snippets.")

        for i, s in enumerate(snippets):
            print(
                f"  {i+1}) ID: {s['id']} | Title: {s['name']} | Time: {s['start_second']}s - {s['end_second']}s")

        if not snippets:
            print("!! No snippets found. Analysis might have been too restrictive.")
            return

    except Exception as e:
        print(f"Failed to get results: {e}")
        return

    # 4. Process the first snippet
    target_snippet = snippets[0]
    print(
        f"\n[Step 3] Triggering video generation for Snippet ID {target_snippet['id']}...")
    try:
        resp = requests.post(
            f"{BASE_URL}/snippets/{target_snippet['id']}/process")
        resp.raise_for_status()
        print(f"Success: {resp.json()['message']}")
    except Exception as e:
        print(f"Failed to trigger snippet processing: {e}")
        return

    print("\n[Step 4] Final Verification...")
    print("Please check the server logs (Celery) to monitor FFmpeg progress.")

    # Wait a bit for FFmpeg to finish actually writing the file after task completion
    time.sleep(5)

    output_path = os.path.join("data", "output", str(session_id), "snippets")
    if os.path.exists(output_path):
        files = os.listdir(output_path)
        print(
            f"Verified: Found {len(files)} files in output directory {output_path}")
        for f in files:
            print(f"  - {f}")
    else:
        print(
            f"!! Warning: Output directory {output_path} not found yet. It might still be rendering.")

    print("\nE2E Test Script Finished.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run E2E Integration test for AIAT Snippets")
    parser.add_argument("link", help="Google Drive link to a video file")
    parser.add_argument(
        "--name", default="E2E Integration Test", help="Session name")

    args = parser.parse_args()
    test_full_flow(args.link, args.name)
