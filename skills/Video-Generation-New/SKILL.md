---
name: Video-Generation-New
description: Video Generation Expert. Generates videos using the grok-imagine-video model. Supports text-to-video, image-to-video, and video-to-video creation. Extensible to additional generation methods in the future.
---

# Video Generation New

Use the `WEDA_API_KEY` environment variable as the token. All video operations are performed via `script/video_gen.py`.

## Behavior

- Always invoke `script/video_gen.py` for all video generation, querying, and downloading. Do not make raw HTTP requests directly.
- The script reads the token from `WEDA_API_KEY` automatically — never pass tokens as arguments.
- After a task completes, display the saved file path and present the video for preview.

### Reference Image Requirement

- **A reference image (`--input-reference`) is mandatory for video generation.** Do not proceed without one.
- If the user does not provide a reference image, ask: *"需要一张参考图来生成视频，是否先用 gtp-image2 生成一张图片作为参考？"*
- If the user agrees, generate the image via `gtp-image2` first, then use the result as `--input-reference` for video generation.
- If the user declines or provides their own image, proceed with whatever reference image is available.

## Prompt Optimization

- Prompts submitted to the model should follow the user's language — use whatever language the user communicates in. Do not forcibly translate to English.
- If the user does not specify anything, the prompt can be optimized appropriately, keeping the user's language.
- If the user requests that the prompt not be altered, use it as-is without any changes.
- **CRITICAL**: Any text enclosed in double quotation marks (`""`) MUST NOT be altered in any way — not a single character may be changed. This includes dialogue, voiceover lines, captions, or any quoted content provided by the user.

## Image Pre-processing (Image-to-Video)

When using `--input-reference`, the reference image **must be pre-processed to match the target video aspect ratio** before submission:

| Target `--size`  | Aspect Ratio | Required image crop/resize |
|------------------|--------------|---------------------------|
| `1280x720`       | 16:9         | Crop/resize image to 16:9 |
| `1280x1280`      | 1:1          | Crop/resize image to 1:1  |
| `960x1280`       | 3:4          | Crop/resize image to 3:4  |
| `720x1280`       | 9:16         | Crop/resize image to 9:16 |

Use `script/resize_image.py` (or PIL/Pillow in a one-liner) to center-crop the image to the correct ratio before calling `create`. This ensures the model receives an image that matches the output canvas — mismatched ratios cause distortion or unwanted letterboxing in the generated video.

Example for a 9:16 video:
```bash
# 1. Pre-process image to 9:16
uv run script/resize_image.py --input photo.jpg --output photo_9x16.jpg --ratio 9:16

# 2. Create video with the pre-processed image
uv run script/video_gen.py create --prompt "A cinematic shot..." --size 720x1280 --input-reference photo_9x16.jpg
```

## Generation Methods

Currently supports **grok** (model: `grok-imagine-video-1.5-preview`). Extensible to additional generation methods in the future.

## Environment Setup

```bash
set WEDA_API_KEY=your_token_here   # Windows
export WEDA_API_KEY=your_token_here  # Linux/macOS
```

## Script Usage (`script/video_gen.py`)

### 1. Create a video task

```bash
uv run script/video_gen.py create --prompt "prompt text" --model grok-imagine-video-1.5-preview --seconds 10 --size 1280x720
```

| Parameter | Required | Description |
|---|---|---|
| `--prompt` | Yes | Video text prompt |
| `--model` | No | Model name, default `grok-imagine-video-1.5-preview` |
| `--seconds` | No | Duration in seconds, max 15 |
| `--size` | No | Resolution: `1280x720` (16:9), `1280x1280` (1:1), `960x1280` (3:4), `720x1280` (9:16) |
| `--input-reference` | **Yes** | Reference image local path (**mandatory**) — **must match target aspect ratio** |
| `--video` | No | Reference video local path (video-to-video) |

Returns JSON; extract the `id` field as the task ID for subsequent queries.

### 2. Query task status (single)

```bash
uv run script/video_gen.py query --id <task_id>
```

Single query, suitable for manual progress checks.

### 3. Poll task status until completion

```bash
uv run script/video_gen.py poll --id <task_id> --interval 3 --timeout 600
```

| Parameter | Default | Description |
|---|---|---|
| `--interval` | 3 | Polling interval in seconds |
| `--timeout` | 600 | Maximum wait time in seconds |
| `--download` | — | Auto-download to specified path upon completion |

**Timeout handling**: If `poll` exits due to timeout (exit code 2), the task is still running — it has not failed. Re-run `poll` or `query` to continue waiting until the task completes. For long-running generations, increase `--timeout` or run multiple times until `status` is `completed`.

Auto-download example:

```bash
uv run script/video_gen.py poll --id <task_id> --timeout 900 --download ./output/
```

### 4. Download video

```bash
uv run script/video_gen.py download --url "<video_url>" --output ./output/video.mp4
```

- `--output` accepts a directory (filename auto-extracted from URL) or a full file path.

## Typical Workflow

```
1. Ensure reference image is available — if not, ask user whether to generate one via gtp-image2
2. Pre-process reference image to match target aspect ratio
3. create  → obtain task_id
4. poll    → wait for completion and auto-download (--download)
5. Display saved file path and video preview to the user
```

If `poll` times out, repeat step 3 until the task completes — no need to resubmit.
