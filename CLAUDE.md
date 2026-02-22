# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Start dev server (serves both API and frontend at http://localhost:8000)
python -m backend.main

# Install dependencies
pip install -r backend/requirements.txt

# Test MiniMax API connectivity
python backend/test_minimax.py

# Docker
docker compose up  # requires .env with MINIMAX_API_KEY

# Required system dependency
# ffmpeg must be installed (brew install ffmpeg / apt install ffmpeg libass-dev)
# libass is needed for subtitle burn-in; videos still work without it
```

No build step, no linting, no test suite. Frontend is a single HTML file served via FastAPI StaticFiles.

## Architecture

Multi-agent video production pipeline. User prompt goes through 6 sequential agents, producing a final MP4.

```
POST /api/create  -->  background thread runs pipeline  -->  SSE via GET /api/stream/{job_id}

Pipeline stages (sequential):
  Director (MiniMax M1 LLM)    -> shot outline JSON
  Script   (MiniMax M1 LLM)    -> production script with video_prompt, narration, subtitle per shot
  Visual   (Hailuo 2.3 video)  -> parallel video clips (ThreadPoolExecutor, max_workers=3)
  Voice    (Speech-2.6-HD TTS) -> sequential narration audio per shot
  Music    (Music-2.0)         -> single background track (optional)
  Editor   (ffmpeg)            -> concat videos, mix audio, burn subtitles -> final.mp4
```

**Key data flow:** Each agent's `run()` returns structured data consumed by the next agent. Director outputs `{title, style, total_duration, shots[]}`. Script enriches each shot with `video_prompt` (optimized for Hailuo), polished `narration`, and `subtitle`. Visual/Voice/Music produce file paths. Editor composites everything via ffmpeg subprocess calls.

**Parallelism model:** `pipeline.py` runs Visual, Voice, Music in a `ThreadPoolExecutor(max_workers=3)`. Visual agent internally uses another `ThreadPoolExecutor(max_workers=3)` to generate individual shots concurrently. Voice generates shots sequentially within its thread.

**Hailuo video generation is async (3-step):** `visual.py` must POST to create a task -> poll `query/video_generation` every 10s (up to 5 min timeout) -> download via `files/retrieve`. Never try to get video results directly from the creation call.

**Shared HTTP session:** `config.py` creates a single `api_session` (requests.Session) with auth headers and 120s default timeout. All agents import and use this session. If you need different timeout for a specific call, pass `timeout=` to the individual request, not to the session.

**Job lifecycle:** `main.py` stores jobs in an in-memory dict. Pipeline runs in `run_in_executor` (background thread). Progress events accumulate in `jobs[job_id]["events"]` list, polled by SSE endpoint every 1s.

**Frontend-backend coupling:** Frontend JS references stages by name (`director`, `script`, `visual`, `voice`, `music`, `editor`) in `stageMap` to highlight corresponding UI cards. These stage names must match `pipeline.py` emit calls.

## Key Conventions

- Every agent module in `backend/agents/` exposes a `run()` function as its sole public interface
- All MiniMax API calls must check `data["base_resp"]["status_code"] != 0` before accessing response payload -- API returns HTTP 200 even on business errors (insufficient balance, rate limit, etc.)
- LLM agents (director, script) strip markdown code fences from responses before JSON parsing
- Frontend uses relative API paths (`/api/...`). FastAPI `app.mount("/", StaticFiles(...))` must be registered after all API routes
- Generated media files go to `backend/output/` (gitignored). Config auto-creates this directory on import
- Environment: single `.env` file at project root with `MINIMAX_API_KEY`
- Editor agent uses `-t` (not `-shortest`) to set output duration, preventing early video truncation

## Mistakes Log

| Mistake | Fix |
|---------|-----|
| MiniMax API 余额不足时 `choices` 为空，取值抛 NoneType | 先检查 `base_resp.status_code != 0` 再取 `choices` |
| `app.mount("/", StaticFiles(...))` 拦截 API 路由 | 必须放在所有 `@app` 路由注册之后 |
| Hailuo video generation 是异步的，直接取结果会失败 | 必须 POST 创建任务 -> 轮询 query 接口 -> 下载文件，三步走 |
