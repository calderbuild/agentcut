"""Music Agent: generates background music via MiniMax Music API."""
import os
import json
from backend.config import MINIMAX_BASE_URL, OUTPUT_DIR, api_session


def run(style: str, mood: str, total_duration: int, on_progress=None) -> str:
    """Generate background music matching the video mood. Returns local file path."""
    if on_progress:
        on_progress("Generating background music...", 0, 1)

    url = f"{MINIMAX_BASE_URL}/music_generation"
    payload = {
        "model": "music-2.0",
        "prompt": (
            f"An instrumental background music track for a {total_duration}-second video. "
            f"Style: {style}. Mood: {mood}. "
            f"No vocals, purely instrumental. Suitable as background music for a short video. "
            f"Cinematic, polished production quality."
        ),
        "lyrics": "[Instrumental]\nBackground music\nCinematic instrumental\nSmooth and polished",
        "audio_setting": {
            "sample_rate": 44100,
            "bitrate": 128000,
            "format": "mp3",
        },
    }

    resp = api_session.post(url, json=payload)
    resp.raise_for_status()
    data = resp.json()

    base_resp = data.get("base_resp", {})
    if base_resp.get("status_code", 0) != 0:
        raise RuntimeError(f"MiniMax Music error: {base_resp.get('status_msg', 'unknown')} (code {base_resp.get('status_code')})")

    if "data" not in data or "audio" not in data["data"]:
        raise RuntimeError(f"Music generation failed: {json.dumps(data)[:500]}")

    audio_bytes = bytes.fromhex(data["data"]["audio"])
    out_path = os.path.join(OUTPUT_DIR, "bgm.mp3")
    with open(out_path, "wb") as f:
        f.write(audio_bytes)

    if on_progress:
        on_progress("Background music ready", 1, 1)

    return out_path
