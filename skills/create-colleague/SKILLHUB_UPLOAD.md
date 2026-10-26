# 赛博同事 / Cyber Colleague 上传检查

这份包已经按市场上传场景做过清洗：  
This package has already been cleaned up for marketplace upload:

- `SKILL.md` 保持在 zip 根目录。  
  `SKILL.md` stays at the zip root.
- 运行所需的 prompts 和 helper tools 会被保留。  
  Runtime prompts and helper tools are included.
- 本地 `colleagues/` 示例或真实数据不会被打进 SkillHub zip。  
  Local `colleagues/` sample or real data is excluded from the SkillHub zip.
- 凭据和 token 应通过环境变量提供，不应写进发布包。  
  Secrets and tokens should be provided through environment variables, not saved into the package.

## 推荐环境变量 / Recommended Environment Variables

- `COLLEAGUE_FEISHU_APP_ID`
- `COLLEAGUE_FEISHU_APP_SECRET`
- `COLLEAGUE_FEISHU_USER_ACCESS_TOKEN`
- `COLLEAGUE_FEISHU_REFRESH_TOKEN`
- `COLLEAGUE_FEISHU_P2P_CHAT_ID`
- `COLLEAGUE_DINGTALK_APP_KEY`
- `COLLEAGUE_DINGTALK_APP_SECRET`
- `COLLEAGUE_SLACK_BOT_TOKEN`

## 生成上传包 / Build The Upload Zip

```bash
python tools/package_skillhub.py
```

默认输出 / Default output:

```text
dist/create-colleague-skillhub-v1.2.1.zip
```

## 上传前检查 / Before Upload

1. zip 能正常打开，且根目录直接看到 `SKILL.md`。  
   The zip opens correctly and shows `SKILL.md` at the archive root.
2. 包内不包含本地 `colleagues/` 示例或真实数据。  
   The archive does not include local `colleagues/` sample or real data.
3. `SKILL.md`、`README*`、`INSTALL.md`、`tools/*.py` 中没有任何真实凭据。  
   No real credentials appear in `SKILL.md`, `README*`, `INSTALL.md`, or `tools/*.py`.
4. 对外标题和说明已经统一为“赛博同事 / Cyber Colleague”。  
   Public-facing titles and descriptions are aligned to “赛博同事 / Cyber Colleague”.
