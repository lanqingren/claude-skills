---
name: GPT-Image2-Generation-Expert
description: A general-purpose image generation tool that supports GPT-Image-2.
---

# GPT-Image2-Generation-Expert

Use the `WEDA_API_KEY` environment variable as the token. All image operations are performed via `script/image_gen.py`.

## Behavior

- Always invoke `script/image_gen.py` for all image generation and downloading. Do not make raw HTTP requests directly.
- The script reads the token from `WEDA_API_KEY` automatically — never pass tokens as arguments.
- After a task completes, display the saved file path and present the image for preview.

## Prompt Optimization

- If the user does not specify anything, the prompt can be optimized appropriately, but the language must remain consistent with that specified by the user.
- If the user requests that the prompt not be altered, it must be submitted exactly as provided by the user.

## Generation interface

- **Without reference image**: Use the `generate` subcommand (JSON request to `/v1/images/generations`).
- **With reference image**: Use the `edit` subcommand (multipart request to `/v1/images/edits`).

See `references/api_generation.md` and `references/api_edits.md` for full parameter details.

## Environment Setup

```bash
set WEDA_API_KEY=your_token_here   # Windows
export WEDA_API_KEY=your_token_here  # Linux/macOS
```

## Script Usage (`script/image_gen.py`)

### 1. Generate image (no reference image)

```bash
uv run script/image_gen.py generate --prompt "prompt text" --size 1024x1024 --quality high --output-dir ./output
```

| 参数 | 必填 | 说明 |
|---|---|---|
| `--prompt` | 是 | 文本提示词 |
| `--model` | 否 | 模型名称，指定 `gpt-image-2` |
| `--n` | 否 | 生成数量，1~10，默认 1 |
| `--size` | 否 | 尺寸，如 `1024x1024`、`1536x1024`、`1024x1536`、`2048x2048` |
| `--quality` | 否 | 质量：`low`、`medium`、`high` |
| `--format` | 否 | 格式：`jpeg`、`png`、`webp` |
| `--output-dir` | 否 | 保存目录，默认当前目录 |

### 2. Edit image (with reference image)

```bash
uv run script/image_gen.py edit --prompt "prompt text" --image photo.jpg --size 1024x1024 --output-dir ./output
```

| 参数 | 必填 | 说明 |
|---|---|---|
| `--prompt` | 是 | 文本提示词 |
| `--image` | 是 | 参考图片路径，可多次指定（多张参考图） |
| `--model` | 否 | 模型名称，指定 `gpt-image-2` |
| `--mask` | 否 | 掩码图片路径（PNG） |
| `--n` | 否 | 生成数量，1~10，默认 1 |
| `--size` | 否 | 尺寸，如 `1024x1024`、`auto` |
| `--quality` | 否 | 质量：`low`、`medium`、`high`、`auto` |
| `--output-dir` | 否 | 保存目录，默认当前目录 |

多张参考图示例：

```bash
uv run script/image_gen.py edit --prompt "combine these images" --image a.jpg --image b.jpg --output-dir ./output
```

### 3. Download image

```bash
uv run script/image_gen.py download --url "<image_url>" --output ./output/image.png
```

- `--output` 接受目录（自动从 URL 提取文件名）或完整文件路径。

## Size Constraints

- 最大边长 ≤ 3840px
- 宽高均须为 16px 的倍数
- 长边与短边之比 ≤ 3:1
- 总像素数在 655360 ~ 8294400 之间

## Typical Workflow

```
# 无参考图
1. generate → 图片自动保存到 --output-dir
2. 向用户展示保存路径和图片预览

# 有参考图
1. edit     → 图片自动保存到 --output-dir
2. 向用户展示保存路径和图片预览
```
