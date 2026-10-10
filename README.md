# AgentCut

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-green.svg)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](Dockerfile)
[![GitHub stars](https://img.shields.io/github/stars/calderbuild/agentcut?style=social)](https://github.com/calderbuild/agentcut)

Turn a text prompt into a finished video. Six AI agents (director, scriptwriter, visual, voice, music, editor) work through a fixed production pipeline and hand back one MP4 with narration, subtitles, and background music.

<p align="center">
  <img src="docs/images/landing.png" width="80%" alt="AgentCut Landing Page" />
</p>

## Demo

There is no hosted demo. AgentCut runs locally with your own MiniMax API key (see [Quick Start](#quick-start)).

- Sample output: [`docs/demo/final.mp4`](docs/demo/final.mp4), a video produced end to end by the pipeline
- Screenshots: the landing page above and the running pipeline below

## How It Works

```
User Prompt
    |
    v
[Director Agent] -- Analyzes creative vision, plans shots
    |
    v
[Script Agent] -- Writes production script with video prompts, narration, subtitles
    |
    +------------------+------------------+
    |                  |                  |
    v                  v                  v
[Visual Agent]    [Voice Agent]     [Music Agent]
 Hailuo Video      Speech TTS        Music Gen
    |                  |                  |
    +------------------+------------------+
    |
    v
[Editor Agent] -- ffmpeg: concat, mix audio, burn subtitles
    |
    v
Final MP4
```

Visual, Voice, and Music agents run **in parallel** after the Script is ready. The Editor waits for all three, then composites the final video.

<p align="center">
  <img src="docs/images/pipeline.png" width="80%" alt="Pipeline Running" />
</p>

## Features

- **Multi-agent SOP** -- 6 specialized agents, each with a single responsibility, orchestrated in a production pipeline
- **Parallel execution** -- Video, voice, and music generation run concurrently to minimize total wait time
- **Real-time progress** -- SSE streaming shows every agent's status with completed/active/pending card states and elapsed timer
- **One prompt, full video** -- From text description to a complete MP4 with narration, subtitles, and background music
- **Style presets** -- 5 one-click preset templates (Tech Product, Travel Vlog, Social Media Ad, Explainer, Brand Story)
- **Script preview** -- Collapsible preview of the production script after the Script agent completes
- **Production summary** -- Total time, shot count, agent count, and a rough API cost estimate displayed after video completion
- **Job isolation** -- Each job gets a separate output directory, enabling safe concurrent production
- **Auto-cleanup** -- Jobs older than 1 hour are automatically cleaned up (memory + disk)
- **Graceful error handling** -- Per-stage error propagation with structured logging and frontend error display

## Tech Stack

| Component | Technology |
|-----------|-----------|
| LLM | MiniMax M1 (Director + Script agents) |
| Video | MiniMax Hailuo 2.3 (1080P, 6s clips) |
| Voice | MiniMax Speech-2.6-HD (TTS with emotion) |
| Music | MiniMax Music-2.0 (instrumental BGM) |
| Composition | ffmpeg (concat, audio mix, subtitles) |
| Backend | Python FastAPI + SSE streaming |
| Frontend | HTML + Tailwind CSS |

## Quick Start

### Prerequisites

- Python 3.10+
- ffmpeg (`brew install ffmpeg` or `apt install ffmpeg`)
- [MiniMax API key](https://www.minimax.io)

### Setup

```bash
git clone https://github.com/calderbuild/agentcut.git
cd agentcut

pip install -r backend/requirements.txt

cp .env.example .env
# Edit .env and add your MiniMax API key
```

### Run

```bash
python -m backend.main
```

Open http://localhost:8000

### Docker

```bash
cp .env.example .env
# Edit .env and add your MiniMax API key

docker compose up
```

## Usage

1. Enter a video description (e.g. "A sunset over Tokyo, cinematic aerial view")
2. Choose duration and shot count
3. Click **Start Production**
4. Watch the 6 agents work in real-time
5. Download the final MP4

## API

| Endpoint | Method | Description |
|---|---|---|
| `/api/create` | POST | Start a production job |
| `/api/stream/{job_id}` | GET | SSE event stream for progress |
| `/api/status/{job_id}` | GET | Poll job status |
| `/api/download/{job_id}` | GET | Download final video |
| `/api/health` | GET | Health check |

### Create a video

```bash
curl -X POST http://localhost:8000/api/create \
  -H "Content-Type: application/json" \
  -d '{"prompt": "A sunset over Tokyo", "duration": 18, "num_shots": 3}'
```

## Cost

Every run spends MiniMax API credits on four kinds of calls: the LLM (Director + Script), one Hailuo video clip per shot, TTS narration, and one music track. Video clips are by far the largest share, so cost grows roughly linearly with the shot count.

The summary card in the UI shows a rough estimate of `0.1 + 3 x shots + 0.2 + 1` CNY (about 10 CNY for a 3-shot video). Treat it as a ballpark only and check [MiniMax pricing](https://www.minimax.io) for current rates. Turning off music skips the music call.

## Troubleshooting

**ffmpeg subtitle filter not available**: If subtitles are not burned into the video, your ffmpeg build lacks `libass`. Install with `brew install ffmpeg` (macOS, usually includes it) or `apt install ffmpeg libass-dev` (Linux). AgentCut will still produce videos without subtitles if the filter is missing.

**API key errors**: Make sure `.env` contains a valid `MINIMAX_API_KEY`. The server will refuse to start if the key is missing.

**Video generation timeout**: Hailuo video generation can take 2-5 minutes per shot. The pipeline polls every 10 seconds with a 5-minute timeout per shot.

**Music generation fails**: Music generation is non-blocking. If it fails, the pipeline continues and the Music card shows an amber "Skipped" state. The final video is produced without background music.

**LLM returns invalid JSON**: Director and Script agents automatically retry once with an explicit "return valid JSON" instruction if the first response fails to parse.

**Concurrent jobs**: Each job writes to its own `backend/output/job_{id}/` directory. Multiple simultaneous productions will not conflict.

## Project Structure

```
backend/
  agents/
    director.py   -- Creative director: prompt -> shot outline
    script.py     -- Scriptwriter: outline -> production script
    visual.py     -- Visual artist: script -> video clips (parallel)
    voice.py      -- Voice artist: script -> narration audio
    music.py      -- Composer: style+mood -> background music
    editor.py     -- Editor: ffmpeg composition
  pipeline.py     -- Agent orchestration (parallel execution)
  main.py         -- FastAPI server + SSE streaming
  config.py       -- Configuration + validation
frontend/
  index.html      -- Single-page app with real-time pipeline UI
```

## Contributing

Bug reports and pull requests are welcome through [GitHub Issues](https://github.com/calderbuild/agentcut/issues). For larger changes, open an issue first so we can agree on the approach.

## Author

Built by [calderbuild](https://github.com/calderbuild), an independent developer. Contact: johnrobertdestiny@gmail.com

## License

[MIT](LICENSE)
