"""Agent orchestration pipeline: Director -> Script -> Visual+Voice+Music -> Editor."""
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Callable

from backend.agents import director, script, visual, voice, music, editor


@dataclass
class PipelineEvent:
    stage: str
    message: str
    progress: float  # 0.0 to 1.0
    data: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


def run_pipeline(
    user_prompt: str,
    duration: int = 30,
    num_shots: int = 3,
    include_music: bool = True,
    on_event: Callable[[PipelineEvent], None] = None,
) -> dict:
    """Run the full video production pipeline.

    Args:
        user_prompt: User's creative description
        duration: Target video duration in seconds
        num_shots: Number of shots to generate
        include_music: Whether to generate background music
        on_event: Callback for progress events

    Returns:
        Dict with output_path and metadata
    """
    def emit(stage, message, progress, data=None):
        if on_event:
            on_event(PipelineEvent(stage, message, progress, data or {}))

    result = {"stages": {}}

    # Stage 1: Director Agent
    emit("director", "Director is analyzing your creative vision...", 0.05)
    outline = director.run(user_prompt, duration, num_shots)
    result["stages"]["director"] = outline
    emit("director", f"Outline ready: {outline['title']} ({len(outline['shots'])} shots)", 0.15,
         {"title": outline["title"], "shots": len(outline["shots"])})

    # Stage 2: Script Agent
    emit("script", "Scriptwriter is crafting detailed production specs...", 0.20)
    production_script = script.run(outline)
    result["stages"]["script"] = production_script
    emit("script", "Production script finalized", 0.30)

    # Stage 3: Visual + Voice + Music (truly parallel)
    emit("visual", "Visual team is generating video clips...", 0.35)

    def visual_progress(msg, current, total):
        p = 0.35 + (current / total) * 0.25
        emit("visual", msg, p)

    def voice_progress(msg, current, total):
        p = 0.60 + (current / total) * 0.10
        emit("voice", msg, p)

    def run_visual():
        return visual.run(production_script, on_progress=visual_progress)

    def run_voice():
        emit("voice", "Voice artist is recording narration...", 0.60)
        return voice.run(production_script, on_progress=voice_progress)

    def run_music():
        if not include_music:
            return None
        emit("music", "Composer is creating background music...", 0.72)
        try:
            mood = outline["shots"][0].get("mood", "inspiring")
            path = music.run(outline["style"], mood, outline["total_duration"])
            emit("music", "Background music composed", 0.78)
            return path
        except Exception as e:
            emit("music", f"Music generation skipped: {e}", 0.78)
            return None

    # Run Visual, Voice, and Music concurrently
    with ThreadPoolExecutor(max_workers=3) as executor:
        visual_future = executor.submit(run_visual)
        voice_future = executor.submit(run_voice)
        music_future = executor.submit(run_music)

        video_results = visual_future.result()
        voice_results = voice_future.result()
        bgm_path = music_future.result()

    result["stages"]["visual"] = [
        {"shot": r["shot_number"], "path": r["video_path"]} for r in video_results
    ]
    result["stages"]["voice"] = [
        {"shot": r["shot_number"], "path": r["audio_path"]} for r in voice_results
    ]
    if bgm_path:
        result["stages"]["music"] = {"path": bgm_path}

    # Stage 4: Editor Agent
    emit("editor", "Editor is compositing the final video...", 0.80)

    def editor_progress(msg, current, total):
        p = 0.80 + (current / total) * 0.18
        emit("editor", msg, p)

    output_path = editor.run(
        video_results, voice_results, production_script,
        bgm_path=bgm_path, on_progress=editor_progress,
    )
    result["output_path"] = output_path
    emit("complete", "Your video is ready!", 1.0, {"output_path": output_path})

    return result
