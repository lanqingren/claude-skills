---
name: TripCue
description: TripCue generates ready-to-use Chinese travel marketing prompts from travel product links across platforms (Spring Tour, Ctrip, Trip.com, etc.) using Playwright DOM extraction first. Use when the user provides a product URL, a product ID, an Atlas/product Markdown fallback, or asks to choose/generate朋友圈、小红书、长图、社群、短视频等旅游营销 Prompt.
metadata:
  short-description: TripCue travel prompt generator
---

# TripCue

Use this skill to turn a travel product link or product ID into ready-to-copy marketing prompts. The required chain is: parse product URL first with Playwright browser rendering; only ask for Markdown when browser/API paths return no usable product content.

## Workflow

1. Extract a stable product identifier from URL or user text:
   - if URL has `productId`, use it
   - if user provides `--product-id`, use it
   - otherwise generate a stable link-based ID automatically
2. Use Playwright browser extraction first:
   - Open the product URL in Chromium.
   - Extract rendered DOM text as the primary product source.
   - Extract product images from DOM image attributes such as `currentSrc`, `src`, `data-src`, and lazy-load attributes.
   - Scroll the page to trigger lazy-loaded content.
   - If Python Playwright or Chromium is missing, install it before reading.
3. API fallback rules:
   - Only Spring Tour links/IDs support structured API fallback.
   - For non-Spring Tour links (e.g., Ctrip/Trip.com), do not call Spring Tour APIs; rely on Playwright or Markdown fallback.
4. If Playwright and APIs still return no usable content (or likely anti-crawl/empty shell page), ask the user to directly paste any product text they already have:
   - no fixed template required
   - a few lines are enough; longer text is better
   - Atlas-exported `.md` is still accepted but not required
   Do not ask for text fallback before attempting Playwright URL parsing.
5. If the user has not specified templates, ask only one AskUserQuestion selection question. If the terminal supports multi-select, enable checkbox/multi-select and process the full selected list, not just the first value. If the terminal only supports single-select, do not show “可多选”; support one template or `全部`. Do not ask users to type template names manually.
6. Do not ask separate follow-up questions for contact, QR code, background, or logo. If optional information is not already provided, omit it.
7. Generate one total index `.md` under:
   `旅游营销Prompt模板/产品生成/{productId}_{产品名}/`
8. Always generate `00_总索引_一键复制.md`, even when only one template is selected. The index must show the full Prompt text inside copyable fenced code blocks. Do not create separate `.txt` files or per-template Prompt `.md/.txt` files.

## Minimal Interaction

When user input is ambiguous (for example they only send `?` or ask “你能做什么”), respond with a short friendly capability intro first, then ask for one next action:
- option A: send a product URL
- option B: paste any product text directly (free-form, no template)
- option C: tell you which template goal they want (朋友圈/小红书/长图/社群/短视频)
Do not force structured fields.

Recommended opening copy (keep it within 3 short sentences):

```text
我可以把旅游产品信息快速生成可直接复制的营销 Prompt（朋友圈、小红书、长图、社群、短视频都支持）。
你可以直接发产品链接，或者直接贴一段产品文案（不用按模板）。
你现在更想先做哪一种？
```

Only ask for template selection when needed. Use AskUserQuestion as a selection UI, not a free-text input. Use exactly this compact menu as selectable options, without numbering or extra explanations.

Selection handling:
- If AskUserQuestion returns an array/list, keep every selected template and join the selected labels with commas when calling `--templates`.
- If `全部` is selected, ignore other selected options and pass `--templates "全部"`.
- Never take only the first selected option from a multi-select result.
- If the current terminal cannot actually return multiple selected options, present the same menu as single-select and remove the “可多选” wording.

```text
请选择要生成的 Prompt 模板：
朋友圈旅游产品海报
小红书旅游产品封面
旅游产品介绍长图
社群推广文案+配图
爆款小红书旅游笔记
高转化旅游产品销售页
旅行社销售朋友圈文案
旅游产品短视频脚本
全部
```

Do not ask about logo, QR code, background image, phone, WeChat, store, or CTA unless the user explicitly asks to add or change those items.

Default handling:

- Contact/sign-up info: omit unless the product page contains it or the user already provided real business contact info.
- Product-link QR code: generate `product_link_qr.png` automatically from the original product URL; if only numeric product ID is provided, use the canonical Spring Tour H5 product URL.
- User-provided QR code: omit unless the user already provided or explicitly requested QR usage.
- Product images: when the product link/API provides product images, download up to the first 3 usable images (JPG/PNG/WEBP/AVIF when available) into the output folder and list them as standard assets.
- Background/hero visual: omit upload-specific wording unless the user already provided or explicitly requested background material usage.

## Template Menu

AskUserQuestion options must be template names, never numbers. The only selectable options are:

```text
朋友圈旅游产品海报
小红书旅游产品封面
旅游产品介绍长图
社群推广文案+配图
爆款小红书旅游笔记
高转化旅游产品销售页
旅行社销售朋友圈文案
旅游产品短视频脚本
全部
```

## Deterministic Generation

Use the bundled script whenever local file output is requested. Keep `--source-mode browser-first` as the business default so Playwright DOM text/images are used first:

```bash
python3 /Users/muxin/.codex/skills/TripCue/scripts/render_prompt_bundle.py \
  --url "https://vacations.ctrip.com/tour/detail/p123456.html" \
  --source-mode browser-first \
  --templates "朋友圈旅游产品海报,小红书旅游产品封面" \
  --output-root "./旅游营销Prompt模板/产品生成" \
  --contact-mode omit \
  --qr-mode omit \
  --background-mode omit
```

Useful options:

- `--product-id 111860` when no URL is available.
- `--source-mode browser-first` to use Playwright first; this is the default.
- `--source-mode api-only` only for Spring Tour numeric product IDs.
- `--no-install-playwright` to prevent automatic Playwright/Chromium installation.
- `--playwright-timeout-ms 35000` to control browser navigation timeout.
- `--templates 全部` to generate all templates.
- `--templates "朋友圈旅游产品海报,小红书旅游产品封面"` to generate selected templates by name.
- `--list-templates` to display template names.
- `--text-file product.md` only after Playwright/API parsing failed and the user provided an Atlas/product Markdown file.
- `--contact-mode omit|custom` based on the user's answer.
- `--phone`、`--wechat`、`--store`、`--cta` when `--contact-mode custom`.
- `--link-qr-mode auto|omit` to generate or skip `product_link_qr.png`; default is `auto`.
- `--qr-mode use|omit`、`--background-mode use|omit` based on user-provided assets.
- `--product-images-mode auto|omit` to include or skip the first 3 product images from the product link; default is `auto`.

## Brand And Asset Rules

Always enforce these rules in generated image prompts:

- Do not include or generate the Spring Tour standard logo.
- Product-link QR: generate `product_link_qr.png` from the product URL or canonical product page URL by default. Keep it as a strict square `1:1` image in prompts; do not stretch, tilt, crop, or perspective-warp it.
- Product images: when available from the product link/API, copy up to the first 3 usable images to the product output folder as `product_image_01.<ext>`, `product_image_02.<ext>`, and `product_image_03.<ext>`. Prompt text may use these images as background, hero base, or collage materials.
- User-provided QR code: if the user selects QR upload, use the user-provided QR PNG in a strict square `1:1` area. Do not stretch, tilt, crop, or perspective-warp it.
- Background: if the user provides a background or hero visual asset, use it as a background, hero base, or collage material when suitable. Do not require any specific filename.
- Prices: display product prices as `￥xx起/人`; keep discount amounts such as `双人共减1000元` unchanged.
- Missing optional information: omit the field and related prompt instructions unless the user explicitly provided it.

## Built-in Assets

- When a product URL or product ID is available, generate `product_link_qr.png` by default. If the Python `qrcode` package is missing, the script installs `qrcode[pil]` automatically.
- When product images are available, copy up to the first 3 product images by default.
- List copied assets in `00_总索引_一键复制.md` under `随附标准素材`.

## WorkBuddy Sharing

If the user wants this skill in WorkBuddy or another business terminal, provide the portable prompt from `references/workbuddy_prompt.md`. In those environments, do not assume Codex skill folders or local scripts are available; instruct the agent to parse the URL first, and for non-Spring Tour links skip Spring Tour APIs and ask for Markdown only when no usable product content is available.
