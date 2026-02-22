"""Editor Agent: composites video clips, voiceover, music, and subtitles via ffmpeg."""
import os
import subprocess
import json
from backend.config import OUTPUT_DIR


def get_media_duration(filepath: str) -> float:
    """Get duration of a media file in seconds using ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", filepath],
        capture_output=True, text=True,
    )
    info = json.loads(result.stdout)
    return float(info["format"]["duration"])


def create_subtitle_file(shots: list, video_durations: list) -> str:
    """Create an SRT subtitle file from shot data."""
    srt_path = os.path.join(OUTPUT_DIR, "subtitles.srt")
    offset = 0.0

    with open(srt_path, "w", encoding="utf-8") as f:
        for i, shot in enumerate(shots):
            duration = video_durations[i] if i < len(video_durations) else shot.get("duration", 6)
            start = offset
            end = offset + duration
            subtitle_text = shot.get("subtitle", shot.get("narration", ""))

            f.write(f"{i + 1}\n")
            f.write(f"{_format_time(start)} --> {_format_time(end)}\n")
            f.write(f"{subtitle_text}\n\n")

            offset = end

    return srt_path


def _format_time(seconds: float) -> str:
    """Format seconds to SRT time format HH:MM:SS,mmm."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def concat_videos(video_paths: list) -> str:
    """Concatenate video clips into a single video."""
    concat_list = os.path.join(OUTPUT_DIR, "concat_list.txt")
    with open(concat_list, "w") as f:
        for path in video_paths:
            f.write(f"file '{os.path.abspath(path)}'\n")

    concat_path = os.path.join(OUTPUT_DIR, "concat.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list,
        "-c", "copy",
        concat_path,
    ], check=True, capture_output=True)
    return concat_path


def concat_audios(audio_paths: list) -> str:
    """Concatenate audio clips into a single audio track."""
    concat_list = os.path.join(OUTPUT_DIR, "audio_concat_list.txt")
    with open(concat_list, "w") as f:
        for path in audio_paths:
            f.write(f"file '{os.path.abspath(path)}'\n")

    concat_path = os.path.join(OUTPUT_DIR, "narration.mp3")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list,
        "-c", "copy",
        concat_path,
    ], check=True, capture_output=True)
    return concat_path


def run(
    video_results: list,
    voice_results: list,
    script: dict,
    bgm_path: str = None,
    on_progress=None,
) -> str:
    """Composite final video with voiceover, music, and subtitles. Returns output path."""
    if on_progress:
        on_progress("Starting video composition...", 0, 4)

    # Step 1: Concatenate video clips
    video_paths = [r["video_path"] for r in video_results]
    concat_video = concat_videos(video_paths)
    if on_progress:
        on_progress("Video clips merged", 1, 4)

    # Step 2: Concatenate voiceover audio
    audio_paths = [r["audio_path"] for r in voice_results]
    concat_audio = concat_audios(audio_paths)
    if on_progress:
        on_progress("Voiceover merged", 2, 4)

    # Step 3: Create subtitles
    video_durations = []
    for vpath in video_paths:
        try:
            video_durations.append(get_media_duration(vpath))
        except Exception:
            video_durations.append(6.0)

    srt_path = create_subtitle_file(script["shots"], video_durations)
    if on_progress:
        on_progress("Subtitles created", 3, 4)

    # Step 4: Final composition
    output_path = os.path.join(OUTPUT_DIR, "final.mp4")
    video_duration = get_media_duration(concat_video)

    filter_parts = []
    inputs = ["-i", concat_video, "-i", concat_audio]
    audio_mix = "[1:a]"

    if bgm_path and os.path.exists(bgm_path):
        inputs.extend(["-i", bgm_path])
        # Mix narration (louder) with BGM (quieter), trim BGM to video length
        audio_mix = "[mixed]"
        filter_parts.append(
            f"[2:a]atrim=0:{video_duration},asetpts=PTS-STARTPTS,volume=0.2[bgm];"
            f"[1:a]volume=1.0[narr];"
            f"[narr][bgm]amix=inputs=2:duration=first[mixed]"
        )

    # Check if subtitles filter is available in ffmpeg
    _has_subtitles_filter = "subtitles" in subprocess.run(
        ["ffmpeg", "-filters"], capture_output=True, text=True,
    ).stdout

    if _has_subtitles_filter:
        subtitle_filter = f"subtitles={srt_path}:force_style='FontSize=24,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,BorderStyle=3,Outline=2,Shadow=0,MarginV=30'"
    else:
        subtitle_filter = None

    if filter_parts:
        if subtitle_filter:
            full_filter = ";".join(filter_parts) + f";[0:v]{subtitle_filter}[outv]"
            v_map = "[outv]"
        else:
            full_filter = ";".join(filter_parts)
            v_map = "0:v"
        cmd = [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", full_filter,
            "-map", v_map, "-map", audio_mix,
            "-c:v", "libx264", "-preset", "fast",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            output_path,
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            *inputs,
        ]
        if subtitle_filter:
            cmd.extend(["-vf", subtitle_filter])
        cmd.extend([
            "-map", "0:v", "-map", "1:a",
            "-c:v", "libx264", "-preset", "fast",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            output_path,
        ])

    subprocess.run(cmd, check=True, capture_output=True)
    if on_progress:
        on_progress("Final video ready!", 4, 4)

    return output_path
