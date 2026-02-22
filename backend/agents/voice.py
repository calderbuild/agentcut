"""Voice Agent: generates voiceover audio via MiniMax TTS API."""
import os
import json
from backend.config import MINIMAX_BASE_URL, OUTPUT_DIR, api_session


def generate_tts(text: str, filename: str, voice_id: str = "English_expressive_narrator", mood: str = "neutral") -> str:
    """Generate TTS audio for text, return local file path."""
    url = f"{MINIMAX_BASE_URL}/t2a_v2"

    # Map mood to emotion parameter
    emotion_map = {
        "inspiring": "happy",
        "dramatic": "sad",
        "calm": "neutral",
        "energetic": "happy",
        "contemplative": "neutral",
        "exciting": "happy",
        "professional": "neutral",
        "warm": "happy",
    }
    emotion = emotion_map.get(mood, "neutral")

    payload = {
        "model": "speech-2.6-hd",
        "text": text,
        "stream": False,
        "voice_setting": {
            "voice_id": voice_id,
            "speed": 1,
            "vol": 1,
            "pitch": 0,
            "emotion": emotion,
        },
        "audio_setting": {
            "sample_rate": 32000,
            "bitrate": 128000,
            "format": "mp3",
            "channel": 1,
        },
    }

    resp = api_session.post(url, json=payload)
    resp.raise_for_status()
    data = resp.json()

    base_resp = data.get("base_resp", {})
    if base_resp.get("status_code", 0) != 0:
        raise RuntimeError(f"MiniMax TTS error: {base_resp.get('status_msg', 'unknown')} (code {base_resp.get('status_code')})")

    if "data" not in data or "audio" not in data["data"]:
        raise RuntimeError(f"TTS failed: {json.dumps(data)[:500]}")

    audio_bytes = bytes.fromhex(data["data"]["audio"])
    out_path = os.path.join(OUTPUT_DIR, filename)
    with open(out_path, "wb") as f:
        f.write(audio_bytes)
    return out_path


def run(script: dict, on_progress=None) -> list:
    """Generate voiceover for all shots. Returns list of audio file paths."""
    shots = script["shots"]
    results = []

    for i, shot in enumerate(shots):
        narration = shot["narration"]
        mood = shot.get("mood", "neutral")
        filename = f"voice_{i + 1}.mp3"
        path = generate_tts(narration, filename, mood=mood)
        results.append({
            "shot_number": shot["shot_number"],
            "audio_path": path,
        })
        if on_progress:
            on_progress(f"Shot {i + 1} voiceover ready", i + 1, len(shots))

    return results
