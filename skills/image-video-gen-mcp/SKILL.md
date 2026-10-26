---
name: image-video-gen-mcp
description: Use when using the imagevideogen MCP server to generate images or videos — covers authentication, which tools to call in order, upload flow, prompt tips, balance queries, recharge flow, and user agreements.
---

# Image-Video-Gen-mcp Skill Reference

## Connection & Authentication

Connect via MCP service `imagevideogen`.

---

## Tool Quick Reference

| Tool | Purpose | Required Parameters |
|---|---|---|
| `get_image_config` | Query available image models/channels/ratios/qualities | — |
| `get_upload_token` | Get a one-time image upload token | — |
| `generate_image` | Submit an image generation task, returns `task_id` | `prompt`, `model` |
| `query_image_task` | Query image task status/results | `task_id` |
| `get_video_config` | Query available video models/channels/ratios/qualities/durations | — |
| `generate_video` | Submit a video generation task, returns `task_id` | `prompt`, `model`, `ratio`, `quality` |
| `query_video_task` | Query video task status/results | `task_id` |
| `get_balance` | Query current user account balance and frozen amount | — |
| `get_balance_logs` | Get balance change history (deductions, recharges, gifts, refunds) | — |
| `create_recharge_order` | Create a recharge order and get payment QR code | `pay_type`, `amount` |
| `query_order_status` | Query recharge order payment status | `order_no` |
| `get_user_agreement` | Retrieve platform agreements and policies (Chinese) | — |

---

## Model Selection

- **Default**: After calling `get_image_config` / `get_video_config`, automatically use the **first model** in the returned list — do not ask the user.
- **User-specified**: If the user explicitly names a model, use that model. If the name is not in the list, inform the user of available models and let them choose.
- **On failure**: When a task fails (`status = failed`), ask the user:
  ```
  Generation failed (reason: {error_msg}).
  Would you like to:
  1. Switch to a different model and retry (available: {model_list})
  2. Retry with the current model
  ```
  Wait for the user's reply before proceeding.

---

## Standard Workflow

> **Do NOT manually select a channel. The optimal channel is auto-selected by default.**

### Image Generation
```
get_image_config                    → Use first model.value (or user-specified model)
[Optional] get_upload_token → POST upload → Get image URL for ref_images
generate_image                      → Get task_id
query_image_task(wait=true)         → Poll for result, get result_url (JSON list)
                                      → Parse JSON array, download each URL to local
                                      → Display downloaded images to user
```

### Video Generation
```
get_video_config                    → Use first model.value (or user-specified model), valid ratio, quality
[Optional] get_upload_token → POST upload → Get image URL for ref_images
generate_video(ratio and quality required) → Get task_id
query_video_task(wait=true)         → Poll for result, get result_url (JSON list)
                                      → Parse JSON array, download each URL to local
                                      → Display downloaded videos to user
```

---

## Image Upload (Two Steps)

1. Call `get_upload_token`, returns `{ token, upload_url }`
2. Upload using the built-in POST tool:
   ```
   POST {upload_url}?token={token}
   Content-Type: multipart/form-data
   Field name: file  (supports jpg/jpeg/png/gif)
   ```
   The `data.url` in the response is the usable image URL — pass it to `ref_images`.

---

## Task Status

| status | Meaning |
|---|---|
| `pending` | Queued |
| `processing` | Generating |
| `completed` | Done — `result_url` is a JSON list of URLs |
| `failed` | Failed — check `error_msg` |

**Timeout & Re-query**: Image default timeout 600 s, video 900 s. Timeout does not mean failure — keep calling `query_*_task(wait=true)` until done.

---

## Result Handling

After `query_*_task` returns `completed`, `result_url` is a **JSON array of URL strings**.

1. Parse `result_url` as a JSON array.
2. **Download each URL to a local file using the download script** (see [Download Script](#download-script) below).
3. Display all downloaded local files to the user (images inline, videos as playable media).
4. **After displaying results, always show a summary line**:
   ```
   ✅ Done | Model: {model_name} | Channel: {channel_name} | Deducted: {cost} pts | Balance: {balance} pts
   ```
   - `model_name`: the model used for generation (e.g. from `generate_image`/`generate_video` params or task result)
   - `channel_name`: from the task result or config (e.g. model/channel field returned by `query_*_task`)
   - `cost`: deducted points — call `get_balance` after task completes and compare with balance before generation, or read from task result if provided
   - `balance`: latest balance from `get_balance`
5. **After the summary line, tell the user where the generated files were saved**:
   ```
   📁 Files saved to: {save_directory}
   ```
   - `save_directory`: the directory path where all generated files were downloaded to

> **IMPORTANT**: Results MUST be downloaded to local files before being shown to the user. Never display raw remote URLs as the final output — always download first, then display the local file.

---

## Download Script

Script location: `server/mcp/script/download_image.py`

### Purpose

Downloads a single image from a remote URL to a specified local path. Use this script for every URL returned in `result_url` after a generation task completes.

### Usage

```bash
python server/mcp/script/download_image.py <image_url> <save_path>
```

| Argument | Description |
|---|---|
| `image_url` | The remote image URL to download |
| `save_path` | Full local path where the file will be saved (directories are created automatically) |

### Examples

```bash
# Download to a specific folder
python server/mcp/script/download_image.py https://cdn.example.com/result.png C:/Downloads/result.png

# Download to the current directory
python server/mcp/script/download_image.py https://cdn.example.com/result.jpg ./result.jpg
```

### Output

On success, the script prints:
```
OK: saved to C:\Downloads\result.png (245.3 KB)
```

On failure, it prints an error to stderr and exits with code 1.

### Integration in Generation Workflow

After `query_image_task` or `query_video_task` returns `completed`:

```
result_url = parse JSON array from task result
for each url in result_url:
    save_path = determine local save path (e.g. ./output/{task_id}_{index}.png)
    run: python server/mcp/script/download_image.py {url} {save_path}
    display the saved local file to the user
show summary line with model, channel, cost, and balance
```

> **No external libraries required.** The script uses only Python standard library (`urllib`, `os`, `sys`) and works with Python 3.6+.

---

## User Account & Balance

### Check Balance

Call `get_balance`:
- `balance` — available compute points
- `frozen` — points locked by in-progress tasks

### Balance History

```
get_balance_logs(page=1, page_size=20)
```

Returns paginated records of deductions, recharges, gifts, and refunds.

---

## Insufficient Balance — Proactive Recharge Prompt

**Trigger**: generation task fails due to insufficient balance, or `get_balance` shows balance too low for the expected task cost.

**⚠️ IMPORTANT: Never proactively create a recharge order. Only create an order after the user explicitly confirms they want to recharge and provides the amount and payment method.**

Prompt the user (friendly reminder only — do NOT call `create_recharge_order` yet):
```
Your compute balance is insufficient. Current balance: {balance} pts.
This task requires approximately {estimated_cost} pts.

Would you like to top up now?
- Amount range: 1–300 yuan (integer), 1 yuan = 100 compute points
- Suggested amount: {suggested_amount} yuan (~{coverage} similar tasks)
- Payment: Alipay or WeChat Pay

Please tell me the amount and payment method, and I will generate a payment QR code.
```

Suggested amount: round up to the nearest 10 yuan covering at least 5 similar tasks, capped at 300 yuan.

**Only proceed to the Recharge Workflow below after the user explicitly replies with an amount and payment method.**

---

## Recharge Workflow

**Prerequisite: User must actively initiate and confirm the recharge request before calling `create_recharge_order`.**

```
User explicitly confirms amount + payment method
  ↓  ← MUST wait for user's explicit confirmation
create_recharge_order(pay_type, amount)
  → Returns: order_no, qr_image (base64 PNG)
  ↓
Render QR code with Markdown image syntax:
  ![支付二维码](data:image/png;base64,...)
  Ask user to scan and pay
  ↓
query_order_status(order_no)   [poll every 5 s, up to 5 min]
  → status 1 = awaiting payment
  → status 2 = paid, balance auto-credited — notify user
  → status 9 = closed/expired — prompt user to create a new order
```

### Recharge Parameters

| Parameter | Details |
|---|---|
| `pay_type` | `1` = Alipay, `2` = WeChat Pay |
| `amount` | Integer yuan, range **1–300** |
| Exchange rate | **1 yuan = 100 compute points** |

**Important**: Always render `qr_image` with Markdown image syntax. Never display the raw base64 string.

### Order Status Codes

| status | Meaning |
|---|---|
| `1` | Awaiting payment |
| `2` | Payment successful, balance credited |
| `9` | Order closed / expired |

---

## User Agreements

Call `get_user_agreement` to retrieve the Chinese-language platform agreements. Surface them proactively on first use, before generating, or when the user asks about policies.

```
get_user_agreement()                 → Returns all 5 agreements
get_user_agreement(type="notice")    → Save-your-results notice
get_user_agreement(type="terms")     → Terms of service
get_user_agreement(type="privacy")   → Privacy policy
get_user_agreement(type="ip")        → Intellectual property statement
get_user_agreement(type="refund")    → Refund & dispute policy
```

Display the returned `content` field verbatim to the user.

---

## Prompt Optimization

### Image
**Structure**: Subject → Style → Lighting → Composition → Details. Elaborate freely unless the user forbids optimization.

### Video
**Structure**: Camera Movement → Subject Action → Scene Environment → Atmosphere.

- Camera: `slow push`, `orbit`, `static shot`, `handheld shake`, `pull focus`
- Duration: 5 s for effects/short cuts; 10–15 s for narrative
- `ratio` and `quality` must come from `get_video_config` — do not guess values
- References: `ref_images` (first frame), `ref_videos` (motion/style), `ref_audio` (voiceover/BGM)
