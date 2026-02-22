"""Director Agent: understands user intent and creates a shot-by-shot outline."""
import json
from backend.config import MINIMAX_BASE_URL, api_session


SYSTEM_PROMPT = """You are the Director of an AI film production team. Your job is to take the user's creative idea and break it down into a detailed shot-by-shot outline for a short video.

For each shot, provide:
1. shot_number: sequential number
2. duration: in seconds (total should match requested length)
3. visual_description: detailed description for AI video generation (style, camera angle, lighting, motion, subject)
4. narration: voiceover text for this shot (in English)
5. mood: emotional tone (e.g. "inspiring", "dramatic", "calm", "energetic")

Also provide:
- title: a short title for the video
- style: overall visual style (e.g. "cinematic sci-fi", "warm documentary", "minimal modern")
- total_duration: total video length in seconds

Respond ONLY with valid JSON. No markdown, no explanation. Example format:
{
  "title": "AI Writing Assistant",
  "style": "cinematic sci-fi with neon accents",
  "total_duration": 30,
  "shots": [
    {
      "shot_number": 1,
      "duration": 10,
      "visual_description": "A writer staring at a blank screen...",
      "narration": "Every great story starts with a blank page.",
      "mood": "contemplative"
    }
  ]
}"""


def run(user_prompt: str, duration: int = 30, num_shots: int = 3) -> dict:
    """Generate a shot outline from user's creative prompt."""
    user_message = (
        f"Create a {duration}-second video with {num_shots} shots.\n"
        f"Theme: {user_prompt}\n"
        f"Each shot should be approximately {duration // num_shots} seconds."
    )

    url = f"{MINIMAX_BASE_URL}/text/chatcompletion_v2"
    payload = {
        "model": "MiniMax-M1",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.7,
        "max_tokens": 2000,
    }

    resp = api_session.post(url, json=payload)
    resp.raise_for_status()
    data = resp.json()

    # Check for API-level errors (e.g. insufficient balance)
    base_resp = data.get("base_resp", {})
    if base_resp.get("status_code", 0) != 0:
        raise RuntimeError(f"MiniMax API error: {base_resp.get('status_msg', 'unknown')} (code {base_resp.get('status_code')})")

    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not content:
        raise RuntimeError("MiniMax API returned empty response")

    # Parse JSON from response (handle potential markdown wrapping)
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

    return json.loads(content)
