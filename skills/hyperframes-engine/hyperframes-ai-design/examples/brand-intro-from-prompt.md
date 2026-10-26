# 示例：品牌介绍序列（3帧）

**用户描述**：做一个 3 帧的品牌介绍视频：第1帧展示 Logo，第2帧展示核心价值观，第3帧是号召行动（CTA）

---

## Step 1：意图解析

```
推断风格：Corporate Clean（品牌感强，专业可信）
内容密度：标准（每帧信息量适中）
运动能量：轻柔（优雅入场，不过度花哨）
色调：明调（白底 + 品牌主色）
每帧时长：帧1 4s / 帧2 6s / 帧3 5s
```

---

## Step 2：设计系统

```
主色：#1a1a2e（深蓝黑）
强调色：#4f46e5（品牌紫）
背景：#f8f7ff（近白，偏品牌紫调）
文字主色：#1a1a2e
文字次色：#64748b
字体：Inter 700（标题）/ Inter 400（正文）
```

---

## ContentGraph JSON

```json
{
  "schemaVersion": 1,
  "intent": "3帧品牌介绍序列：Logo → 价值观 → CTA",
  "nodes": [
    {
      "id": "frame-logo",
      "kind": "entity",
      "label": "Logo 帧",
      "frameIntent": "展示品牌 Logo 和品牌名，建立品牌认知",
      "durationSec": 4.0
    },
    {
      "id": "frame-values",
      "kind": "text",
      "label": "价值观帧",
      "frameIntent": "展示3个核心价值观，逐一飞入",
      "durationSec": 6.0
    },
    {
      "id": "frame-cta",
      "kind": "entity",
      "label": "CTA 帧",
      "frameIntent": "号召用户行动，展示联系方式",
      "durationSec": 5.0
    }
  ],
  "edges": [
    {"from": "frame-logo",   "to": "frame-values", "kind": "sequence"},
    {"from": "frame-values", "to": "frame-cta",    "kind": "sequence"}
  ]
}
```

**generate_content_graph 调用**：

```json
{
  "tool": "generate_content_graph",
  "arguments": {
    "project_id": "proj_xxx",
    "graph_json": "<上方 JSON 字符串>"
  }
}
```

---

## 帧 1：Logo 展示

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{width:1920px;height:1080px;overflow:hidden;background:#f8f7ff;font-family:'Inter',system-ui,sans-serif}
.background-layer{position:absolute;inset:0;background:#f8f7ff}
.decoration-layer{position:absolute;inset:0}
.deco-circle-1{position:absolute;top:-120px;right:-120px;width:500px;height:500px;border-radius:50%;background:#4f46e5;opacity:0.08}
.deco-circle-2{position:absolute;bottom:-80px;left:-80px;width:320px;height:320px;border-radius:50%;border:2px solid #4f46e5;opacity:0.12}
.deco-line{position:absolute;top:50%;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,#4f46e5,transparent);opacity:0.15;transform:translateY(-1px)}
.content-layer{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:24px}
.logo-mark{width:120px;height:120px;background:#4f46e5;border-radius:24px;display:flex;align-items:center;justify-content:center;opacity:0;transform:scale(0.6)}
.logo-mark span{font-size:60px;color:#fff;font-weight:700;line-height:1}
.brand-name{font-size:80px;font-weight:700;color:#1a1a2e;letter-spacing:-2px;opacity:0;transform:translateY(40px)}
.brand-tagline{font-size:28px;color:#64748b;font-weight:400;opacity:0;transform:translateY(20px)}
</style>
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
</head>
<body>
<div class="background-layer" aria-hidden="true"></div>
<div class="decoration-layer" aria-hidden="true">
  <div class="deco-circle-1"></div>
  <div class="deco-circle-2"></div>
  <div class="deco-line"></div>
</div>
<div class="content-layer">
  <div class="logo-mark"><span>B</span></div>
  <h1 class="brand-name">BrandName</h1>
  <p class="brand-tagline">构建更好的未来</p>
</div>
<script>
window.__timelines = window.__timelines || [];
const tl = gsap.timeline();
window.__timelines.push(tl);

// 装饰件 ambient motion
gsap.to('.deco-circle-1', {rotation:360,duration:40,repeat:-1,ease:'none',transformOrigin:'center center'});
gsap.to('.deco-circle-2', {scale:1.08,duration:4,repeat:-1,yoyo:true,ease:'sine.inOut'});

// 入场动画
tl.to('.logo-mark',   {opacity:1,scale:1,duration:0.6,ease:'back.out(1.7)'})
  .to('.brand-name',  {opacity:1,y:0,duration:0.6,ease:'power2.out'},'-=0.2')
  .to('.brand-tagline',{opacity:1,y:0,duration:0.5,ease:'power2.out'},'-=0.3');
</script>
</body>
</html>
```

---

## 帧 2：核心价值观

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{width:1920px;height:1080px;overflow:hidden;background:#f8f7ff;font-family:'Inter',system-ui,sans-serif}
.background-layer{position:absolute;inset:0;background:#f8f7ff}
.decoration-layer{position:absolute;inset:0}
.deco-rect-1{position:absolute;top:0;left:0;width:8px;height:100%;background:#4f46e5;opacity:0.15}
.deco-rect-2{position:absolute;top:0;right:0;width:8px;height:100%;background:#4f46e5;opacity:0.08}
.deco-dot{position:absolute;top:80px;right:160px;width:16px;height:16px;border-radius:50%;background:#4f46e5;opacity:0.20}
.content-layer{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:48px;padding:0 120px}
.section-label{font-size:28px;color:#64748b;font-weight:400;letter-spacing:4px;text-transform:uppercase;opacity:0}
.values-row{display:flex;gap:80px;align-items:flex-start}
.value-item{flex:1;display:flex;flex-direction:column;gap:16px;opacity:0;transform:translateY(50px)}
.value-number{font-size:64px;font-weight:700;color:#4f46e5;line-height:1}
.value-title{font-size:40px;font-weight:700;color:#1a1a2e;line-height:1.2}
.value-desc{font-size:28px;color:#64748b;line-height:1.6}
.divider{width:48px;height:4px;background:#4f46e5;border-radius:2px}
</style>
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
</head>
<body>
<div class="background-layer" aria-hidden="true"></div>
<div class="decoration-layer" aria-hidden="true">
  <div class="deco-rect-1"></div>
  <div class="deco-rect-2"></div>
  <div class="deco-dot"></div>
</div>
<div class="content-layer">
  <p class="section-label">核心价值观</p>
  <div class="values-row">
    <div class="value-item">
      <div class="value-number">01</div>
      <div class="divider"></div>
      <h2 class="value-title">以用户为中心</h2>
      <p class="value-desc">每一个决策都从用户需求出发，持续创造真实价值</p>
    </div>
    <div class="value-item">
      <div class="value-number">02</div>
      <div class="divider"></div>
      <h2 class="value-title">极致品质</h2>
      <p class="value-desc">对细节的执着追求，是我们区别于平庸的根本</p>
    </div>
    <div class="value-item">
      <div class="value-number">03</div>
      <div class="divider"></div>
      <h2 class="value-title">持续创新</h2>
      <p class="value-desc">拥抱变化，敢于突破，让明天比今天更好</p>
    </div>
  </div>
</div>
<script>
window.__timelines = window.__timelines || [];
const tl = gsap.timeline();
window.__timelines.push(tl);

// 装饰件 ambient motion
gsap.to('.deco-dot', {scale:1.5,opacity:0.1,duration:2,repeat:-1,yoyo:true,ease:'sine.inOut'});
gsap.to('.deco-rect-1', {scaleY:0.95,duration:3,repeat:-1,yoyo:true,ease:'sine.inOut',transformOrigin:'top center'});

// 入场动画（逐一飞入）
const items = document.querySelectorAll('.value-item');
tl.to('.section-label', {opacity:1,duration:0.5,ease:'power2.out'})
  .to(items[0], {opacity:1,y:0,duration:0.6,ease:'power2.out'}, '+=0.2')
  .to(items[1], {opacity:1,y:0,duration:0.6,ease:'power2.out'}, '-=0.3')
  .to(items[2], {opacity:1,y:0,duration:0.6,ease:'power2.out'}, '-=0.3');
</script>
</body>
</html>
```

---

## 帧 3：CTA

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{width:1920px;height:1080px;overflow:hidden;background:#1a1a2e;font-family:'Inter',system-ui,sans-serif}
.background-layer{position:absolute;inset:0;background:#1a1a2e}
.decoration-layer{position:absolute;inset:0}
.deco-glow{position:absolute;top:50%;left:50%;width:800px;height:800px;border-radius:50%;background:radial-gradient(circle,#4f46e520 0%,transparent 70%);transform:translate(-50%,-50%);opacity:0.6}
.deco-ring-1{position:absolute;top:50%;left:50%;width:600px;height:600px;border:1px solid #4f46e5;border-radius:50%;transform:translate(-50%,-50%);opacity:0.10}
.deco-ring-2{position:absolute;top:50%;left:50%;width:900px;height:900px;border:1px solid #4f46e5;border-radius:50%;transform:translate(-50%,-50%);opacity:0.06}
.content-layer{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:32px}
.cta-eyebrow{font-size:28px;color:#818cf8;font-weight:400;letter-spacing:3px;text-transform:uppercase;opacity:0}
.cta-headline{font-size:88px;font-weight:700;color:#f8f7ff;text-align:center;line-height:1.1;opacity:0;transform:translateY(40px)}
.cta-headline em{color:#818cf8;font-style:normal}
.cta-contact{display:flex;gap:64px;margin-top:16px;opacity:0}
.contact-item{display:flex;flex-direction:column;align-items:center;gap:8px}
.contact-label{font-size:24px;color:#64748b;font-weight:400}
.contact-value{font-size:32px;color:#f8f7ff;font-weight:600}
</style>
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
</head>
<body>
<div class="background-layer" aria-hidden="true"></div>
<div class="decoration-layer" aria-hidden="true">
  <div class="deco-glow"></div>
  <div class="deco-ring-1"></div>
  <div class="deco-ring-2"></div>
</div>
<div class="content-layer">
  <p class="cta-eyebrow">立即开始</p>
  <h1 class="cta-headline">让我们一起<em>创造</em><br>更好的未来</h1>
  <div class="cta-contact">
    <div class="contact-item">
      <span class="contact-label">官网</span>
      <span class="contact-value">www.brand.com</span>
    </div>
    <div class="contact-item">
      <span class="contact-label">邮箱</span>
      <span class="contact-value">hello@brand.com</span>
    </div>
  </div>
</div>
<script>
window.__timelines = window.__timelines || [];
const tl = gsap.timeline();
window.__timelines.push(tl);

// 装饰件 ambient motion
gsap.to('.deco-ring-1', {rotation:360,duration:30,repeat:-1,ease:'none',transformOrigin:'center center'});
gsap.to('.deco-ring-2', {rotation:-360,duration:50,repeat:-1,ease:'none',transformOrigin:'center center'});
gsap.to('.deco-glow',   {scale:1.1,opacity:0.4,duration:4,repeat:-1,yoyo:true,ease:'sine.inOut'});

// 入场动画
tl.to('.cta-eyebrow',  {opacity:1,duration:0.5,ease:'power2.out'})
  .to('.cta-headline', {opacity:1,y:0,duration:0.7,ease:'power2.out'},'-=0.2')
  .to('.cta-contact',  {opacity:1,duration:0.6,ease:'power3.in'},'-=0.1');
</script>
</body>
</html>
```

---

## generate_frames 调用

```json
{
  "tool": "generate_frames",
  "arguments": {
    "project_id": "proj_xxx",
    "frames": "[{\"node_id\":\"frame-logo\",\"html_content\":\"<帧1 HTML>\",\"duration_sec\":4},{\"node_id\":\"frame-values\",\"html_content\":\"<帧2 HTML>\",\"duration_sec\":6},{\"node_id\":\"frame-cta\",\"html_content\":\"<帧3 HTML>\",\"duration_sec\":5}]"
  }
}
```

---

## 保存为模板

此 3 帧序列适合保存为模板，可变量化：
- `brand_name`（BrandName）
- `brand_tagline`（构建更好的未来）
- `brand_color`（#4f46e5）
- `value_1_title` / `value_2_title` / `value_3_title`
- `cta_headline`
- `website` / `email`

参考 `references/save-as-template.md` 了解完整保存流程。
