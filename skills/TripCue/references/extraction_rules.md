# Extraction Rules

## Source Priority

1. Playwright-rendered product page (all platforms):
   - extract rendered DOM text as the primary source for product name, destination, days, price, highlights, and itinerary text
   - extract images from DOM `<img>` attributes such as `currentSrc`, `src`, `data-src`, `data-original`, and lazy-load attributes
   - scroll to trigger lazy-loaded page content
   - optionally merge network response data only to fill missing fields; do not prefer API over usable DOM text
2. Spring Tour structured API data only when:
   - the input is a Spring Tour link or numeric Spring Tour product ID
   - and Playwright cannot read usable DOM content
3. Atlas-exported or product-page Markdown, only after Playwright/API parsing returns no usable content.
4. User-pasted product text (free-form, no fixed template), only after Playwright/API parsing returns no usable content.

Never request text fallback before attempting to parse the product URL or product ID with Playwright.

## Core Fields

Extract or infer:

- product id
- product URL
- source platform
- product name
- destination
- origin city
- days and nights
- min price
- departure dates and prices
- recommend/highlight text
- discount text
- itinerary days
- included/excluded fee notes
- images from DOM first; API images only as optional supplement
- contact information

## Optional Supplemental Information

If a field is not available from the product link or Markdown fallback, do not silently invent it.

Do not ask separate follow-up questions for optional supplemental fields. Use these defaults:

- Contact/sign-up info: omit unless the product page contains it or the user already provided real business contact info.
- Product-link QR code: generate automatically from the original product URL; if only numeric Spring Tour product ID is provided, use the canonical Spring Tour H5 product URL.
- User-provided QR code PNG: omit unless the user already provided or explicitly requested QR usage.
- Background image: omit upload-specific wording unless the user already provided or explicitly requested background material usage.
- Product images: if product images are available from DOM or API, output up to the first 3 usable images (JPG/PNG/WEBP/AVIF) as standard assets without asking the user.
- Logo rule: do not include Spring Tour standard logo by default.

## Normalization

- Prices: `￥18,999起/人`
- Departure rows: `2026-06-30 周二 ￥18,999起/人`
- Discounts: keep raw discount wording, e.g. `提前90天报名，双人共减1000元`
- Product images: save up to 3 images as `product_image_01.<ext>`, `product_image_02.<ext>`, and `product_image_03.<ext>`; list them in the total index under `随附标准素材`.
- Product-link QR code: save as `product_link_qr.png`; list it in the total index under `随附标准素材`.
- If contact info is missing, omit phone, WeChat, store, sign-up wording, and QR sign-up language.
- If destination cannot be confidently split, keep the title-derived destination text.
- Prefer concise, image-prompt-friendly highlights over long legal or booking text.

## Image Prompt Rules

- Do not include or generate Spring Tour logo assets.
- Use the generated product-link QR `product_link_qr.png` as a strict square `1:1` asset in bottom consultation/sign-up areas.
- Use downloaded real product images as background, hero base, or collage materials when they are available.
- QR code must be square `1:1` only when the user already provided or explicitly requested QR PNG usage.
- The provided background or hero visual asset may be used as a background, hero image, or collage source only when the user already provided or explicitly requested it. Do not require any specific filename.
- Avoid telling the image model to generate a fake QR code.
