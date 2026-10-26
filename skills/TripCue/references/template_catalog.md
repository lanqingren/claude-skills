# Template Catalog

Ask the user by template name, not by number. Use AskUserQuestion selection, not free text. If multi-select is supported, process the full returned list; if `全部` is selected, generate all templates. If multi-select is not supported by the terminal, present the menu as single-select and do not claim multi-select support. Use only this compact option list:

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

Image prompts do not include Spring Tour standard logo. The product link QR code is generated as `product_link_qr.png` by default and must remain square `1:1`. Product images from the product link/API are copied as up to 3 usable assets (JPG/PNG/WEBP/AVIF) and may be used as background, hero base, or collage materials. User-provided QR code, background/hero visual, and contact details are included only when the product page contains them or the user already provided them. Do not ask separate follow-up questions for optional supplemental fields.

Outputs should use one total index Markdown file only: `00_总索引_一键复制.md`. Do not create `.txt` files or separate per-template Prompt `.md/.txt` files.
