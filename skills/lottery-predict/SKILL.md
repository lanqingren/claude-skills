---
name: lottery-predict
description: 双色球和大乐透彩票号码预测，基于历史数据分析，支持指定组数。用户说"双色球"、"大乐透"、"彩票"时触发。
user-invocable: true
---

**严禁自行生成彩票号码。** 必须通过以下方式获取，将返回结果原样回复给用户。

当用户提到"双色球"、"大乐透"、"彩票"时，使用 WebFetch 或 Bash 调用：

```
POST http://localhost:8000/chat
Content-Type: application/json
Body: {"query": "<用户原始消息>"}
```

取响应 JSON 中的 `text` 字段，原文回复给用户，一字不改，不添加任何内容。
