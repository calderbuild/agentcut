"""Visual Agent: generates video clips via MiniMax Hailuo API."""
import os
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from backend.config import MINIMAX_BASE_URL, OUTPUT_DIR, api_session


def create_video_task(prompt: str, duration: int = 6) -> str:
    """Submit a video generation task, return task_id."""
    url = f"{MINIMAX_BASE_URL}/video_generation"
    payload = {
        "prompt": prompt,
        "model": "MiniMax-Hailuo-2.3",
        "duration": min(duration, 6),  # Hailuo supports 6s or 10s
        "resolution": "1080P",
    }
    resp = api_session.post(url, json=payload)
    resp.raise_for_status()
    data = resp.json()
    base_resp = data.get("base_resp", {})
    if base_resp.get("status_code", 0) != 0:
        raise RuntimeError(f"MiniMax API error: {base_resp.get('status_msg', 'unknown')} (code {base_resp.get('status_code')})")
    task_id = data.get("task_id", "")
    if not task_id:
        raise RuntimeError(f"Video task creation failed: {data}")
    return task_id


def poll_task(task_id: str, max_wait: int = 300) -> str:
    """Poll until video generation completes, return file_id."""
    url = f"{MINIMAX_BASE_URL}/query/video_generation"
    start = time.time()
    while time.time() - start < max_wait:
        time.sleep(10)
        resp = api_session.get(url, params={"task_id": task_id})
        data = resp.json()
        status = data.get("status", "Unknown")
        if status == "Success":
            return data["file_id"]
        elif status == "Fail":
            raise RuntimeError(f"Video generation failed: {data.get('error_message')}")
    raise TimeoutError(f"Video generation timed out after {max_wait}s")


def download_file(file_id: str, filename: str) -> str:
    """Download video file by file_id, return local path."""
    url = f"{MINIMAX_BASE_URL}/files/retrieve"
    resp = api_session.get(url, params={"file_id": file_id})
    resp.raise_for_status()
    download_url = resp.json()["file"]["download_url"]

    out_path = os.path.join(OUTPUT_DIR, filename)
    video_resp = requests.get(download_url)
    with open(out_path, "wb") as f:
        f.write(video_resp.content)
    return out_path


def generate_single_shot(shot: dict, index: int) -> dict:
    """Generate video for a single shot. Returns dict with shot info and local path."""
    prompt = shot["video_prompt"]
    duration = shot.get("duration", 6)

    task_id = create_video_task(prompt, duration)
    file_id = poll_task(task_id)
    filename = f"shot_{index + 1}.mp4"
    local_path = download_file(file_id, filename)

    return {
        "shot_number": shot["shot_number"],
        "video_path": local_path,
        "duration": duration,
    }


def run(script: dict, on_progress=None) -> list:
    """Generate video clips for all shots in parallel. Returns list of shot results."""
    shots = script["shots"]
    results = [None] * len(shots)

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {}
        for i, shot in enumerate(shots):
            future = executor.submit(generate_single_shot, shot, i)
            futures[future] = i

        for future in as_completed(futures):
            idx = futures[future]
            result = future.result()
            results[idx] = result
            if on_progress:
                on_progress(f"Shot {idx + 1} video ready", idx + 1, len(shots))

    return results
