---
name: paper-reference-formatter
description: Format academic reference entries from user-provided journal article, thesis/dissertation, conference paper, book, report, preprint, or web literature metadata. Use when a user wants bibliography/reference-list entries converted, normalized, checked, or batch-formatted in GB/T 7714, APA, MLA, or Chicago style, especially when the user asks to choose a citation style or provides incomplete Chinese/English paper metadata.
---

# Paper Reference Formatter

## Workflow

1. Identify the requested output style: GB/T 7714, APA, MLA, or Chicago. If the style is missing, ask the user to choose one before formatting.
2. Parse each source into structured fields: reference type, authors, title, container title, year, volume, issue, pages, publisher, place, institution, DOI, URL, access date, language, and edition when present.
3. Infer the reference type conservatively from clues:
   - Journal article: journal name, volume/issue/pages, DOI.
   - Thesis/dissertation: degree type, university/institution, place, "硕士/博士/学位论文", dissertation/thesis.
   - Conference paper: conference/proceedings name, location, date, editors, pages.
   - Book: publisher, place, edition, ISBN, no journal/container.
   - Report/preprint/webpage: report number, arXiv/bioRxiv/SSRN, URL, access date.
4. Preserve user-provided facts. Do not invent missing bibliographic data. If a required field is missing, either omit it when the style allows omission or mark it as `[missing: field]` if the omission would make the entry misleading.
5. Normalize names, dates, titles, punctuation, and identifiers according to the chosen style. For Chinese references, preserve Chinese names and titles unless the user requests translation.
6. Output a clean numbered list by default. Add a short "Needs confirmation" note only for entries with unresolved missing or ambiguous fields.

## Formatting Resources

- Read `references/style-rules.md` when exact punctuation, field order, or type-specific templates are needed.
- Use `scripts/format_reference.py` for deterministic formatting when the user's data can be represented as JSON records. The script supports `gbt7714`, `apa`, `mla`, and `chicago`.

Example script usage:

```bash
python scripts/format_reference.py --style apa --input refs.json
```

Input JSON may be a single object or a list of objects:

```json
{
  "type": "journal",
  "authors": ["Zhang Wei", "Li Ming"],
  "title": "Research on citation formatting",
  "year": "2024",
  "container": "Journal of Academic Writing",
  "volume": "12",
  "issue": "3",
  "pages": "45-58",
  "doi": "10.1234/example"
}
```

## Quality Checks

- Keep each final entry in the selected style only; do not mix styles.
- Ensure author order is unchanged from the input.
- Ensure DOI is normalized as `https://doi.org/...` for APA, MLA, and Chicago when present.
- For GB/T 7714, include the document type marker where applicable: `[J]`, `[D]`, `[C]`, `[M]`, `[R]`, `[EB/OL]`, or `[A]`.
- For APA, use sentence case for article/thesis titles when clearly possible; keep proper nouns and original capitalization in Chinese titles.
- For MLA and Chicago, use headline-style title capitalization only when the input already supports it confidently; otherwise preserve title capitalization.
- Report unresolved ambiguity briefly after the formatted list instead of interrupting the list.
