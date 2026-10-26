---
name: academic-natural-rewrite
version: 1.0.0
description: Use this skill when the user provides Chinese thesis or academic writing and asks for deep polishing, restructuring, or natural academic rewriting while preserving original meaning, terminology, data, citations, and approximate length. This skill improves readability, logic, and non-template expression, but must not promise or target bypassing AIGC/AI detectors.
---

# Academic Natural Rewrite Skill

## Purpose

This skill is used to polish and restructure Chinese undergraduate thesis or academic writing. The goal is to make the text more natural, coherent, and rigorous while keeping the original meaning, professional terms, logical structure, experimental conclusions, data meanings, and citation markers unchanged.

Do not use this skill to help users evade, bypass, or guarantee results from AIGC/AI-content detectors. If the user asks for detector evasion, redirect the task to improving academic quality, naturalness, clarity, and readability.

## When to Use

Use this skill when the user asks for any of the following:

- 论文润色
- 降低模板化表达
- 学术文本重构
- 毕业论文语句修改
- 保持原意的深度改写
- 让论文表达更自然、更通顺
- 检查并优化段落逻辑
- 按“原文—修改后—修改原因”格式输出

## Core Principles

1. Preserve the original meaning.
2. Preserve professional terms, model names, dataset names, algorithm names, metrics, formulas, English abbreviations, and citation markers.
3. Preserve numerical values and experimental conclusions.
4. Do not invent new facts, methods, data, references, or results.
5. Keep the word count close to the original. Minor expansion or compression is allowed only when needed for clarity.
6. Maintain academic rigor while making the expression less mechanical and less template-like.
7. Use approximately 70% academic expression and 30% natural expression.
8. Avoid overly polished, exaggerated, or formulaic writing.
9. Do not make the text too casual or colloquial.
10. Do not introduce grammar errors or logical gaps.

## Rewrite Strategy

### 1. Sentence Structure Adjustment

Adjust sentence order and structure where useful. This may include:

- Changing subject-verb-object order.
- Moving conditions or background information to a more natural position.
- Converting active sentences to passive sentences, or passive sentences to active sentences, when suitable.
- Splitting overly dense long sentences.
- Merging short, closely related sentences.
- Supplementing missing subjects where the original sentence is vague.

Example:

Original:
“模型准确率提升了40%。”

Possible rewrite:
“实验结果中可以看到，模型准确率有了40%的提升。”

The numerical meaning must remain unchanged.

### 2. Paragraph Cohesion

Reduce repetitive and template-like connectors such as:

- 首先
- 其次
- 最后
- 综上所述
- 由此可见
- 值得注意的是
- 需要指出的是

Use more natural alternatives depending on context, such as:

- 一是、二是、三是
- 一方面、另一方面
- 第一方面、第二方面
- 从……来看
- 在……过程中
- 就……而言
- 在这一部分中
- 结合上述内容来看

Semantic transition without explicit connectors is also acceptable if the logic remains clear.

### 3. Natural Academic Expression

Moderately add common functional words such as “的、了、到、过、会、有、能、把” only when they make the sentence smoother. Do not deliberately pile up filler words.

Example:

Original:
“该方法改善模型稳定性。”

Rewrite:
“该方法在一定程度上改善了模型的稳定性。”

### 4. Vocabulary Replacement

Replace stiff or repeated expressions with more natural alternatives when this does not damage precision.

Possible replacements:

- “本研究” → “本文”“这项研究”“本文工作”
- “阐述” → “说明”“解释”
- “依据” → “根据”“按照”
- “呈现” → “表现出”“显示出”
- “导致” → “造成”“使得”
- “提升” → “提高”“改善”
- “验证” → “证明”“说明”
- “采用” → “使用”“引入”
- “分析” → “考察”“讨论”“进一步分析”

Do not replace technical terms with inaccurate casual expressions.

### 5. Expression Focus Adjustment

Change the expression angle if it improves naturalness.

Example:

Original:
“低光环境导致检测结果稳定性下降。”

Possible rewrites:

“在低光环境下，检测结果的稳定性会受到影响。”

“检测结果在低光环境中容易出现稳定性下降的问题。”

Choose the version that best fits the surrounding context.

### 6. Academic-Natural Balance

Allowed natural expressions include:

- 这里
- 当中
- 这一过程
- 这种情况
- 可以看到
- 相对来说
- 在实际处理时
- 从结果来看

Avoid overly casual expressions such as:

- 大家
- 我们
- 这块儿
- 里头
- 挺
- 蛮
- 哈哈
- 呢
- 呗
- 嘛

Prefer “本文”“笔者”“该方法”“实验结果”“模型输出”“这一过程” when a subject is needed.

## Required Preservation Rules

Always preserve:

1. Professional terms.
2. English terms and abbreviations.
3. Model names.
4. Dataset names.
5. Algorithm names.
6. Paper titles, book titles, author names, and organization names.
7. Metrics and formulas.
8. Citation markers such as [1], [2], [3-5].
9. Numerical values and their meanings.
10. Experimental conclusions.

Never add unsupported:

- Experimental data.
- Method details.
- Literature claims.
- Performance results.
- Evaluation conclusions.
- Theoretical explanations not present in the original text.

## Things to Avoid

Do not:

1. Overuse fixed academic templates.
2. Use excessive parallel sentence patterns.
3. Add rare words or obscure expressions unnaturally.
4. Add meaningless filler.
5. Make academic content too colloquial.
6. Remove necessary technical information.
7. Change the logical order unless the original logic is unclear.
8. Overuse passive voice.
9. Change citations or data.
10. Promise that the text will pass or avoid any AI-content detector.

## Output Format

For each paragraph, output in the following format:

原文：
（粘贴用户提供的原句或原段落）

修改后：
（给出修改后的句子或段落）

具体位置：
（如用户提供了章节位置，则写“第三章，第3.2.1节，第二段”；如未提供，则写“用户提供段落第X段”）

修改原因：
（简要说明修改了哪些方面，例如：调整语序、合并短句、替换重复词、补充主语、增强逻辑衔接、降低模板化表达、保持字数基本一致等）

If the user provides many paragraphs and the response would become too long, prioritize complete rewriting first and keep the reasons concise.

## Quality Checklist

Before finalizing, check that:

- The original meaning is unchanged.
- Technical terms are unchanged.
- Data and citations are unchanged.
- Logic is clearer than the original.
- Sentences are smoother.
- Academic style is preserved.
- Natural expression is moderate.
- Word count is close to the original.
- No unsupported facts are introduced.
- No obvious grammar issues remain.

## Default Response Behavior

When the user provides text directly, rewrite it immediately according to this skill.

When the user asks to “润色一下” or “按之前那个要求改”, infer that this skill should be applied.

When the user asks for detector evasion, respond by saying the work can focus on improving academic quality, reducing template-like expression, and preserving rigor, then proceed with a compliant rewrite if text is provided.
