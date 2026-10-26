# Citation Style Rules

Use these templates as practical formatting guides. Preserve known data; do not fabricate missing fields.

## Shared Parsing

Common fields:

- `type`: `journal`, `thesis`, `conference`, `book`, `report`, `preprint`, `webpage`
- `authors`: ordered list of author names
- `title`: work title
- `container`: journal, proceedings, website, or series title
- `year`, `date`, `volume`, `issue`, `pages`
- `publisher`, `place`, `institution`, `degree`
- `doi`, `url`, `accessed`

Name handling:

- Chinese names: keep as provided, usually no comma inversion.
- Western names in APA: invert to `Family, Initials.` when parseable.
- Western names in MLA/Chicago bibliography: invert first author only when parseable; keep later authors in normal order.
- If name parsing is uncertain, preserve the input name string.

## GB/T 7714

Prefer GB/T 7714 reference-list patterns with document markers.

Journal:

`Authors. Title[J]. Journal, Year, Volume(Issue): Pages. DOI/URL.`

Thesis:

`Author. Title[D]. Place: Institution, Year.`

Conference paper:

`Authors. Title[C]//Proceedings title. Place: Publisher, Year: Pages.`

Book:

`Authors. Title[M]. Edition. Place: Publisher, Year.`

Report:

`Authors. Title[R]. Place: Institution/Publisher, Year.`

Webpage:

`Authors. Title[EB/OL]. (Published date)[Accessed date]. URL.`

Notes:

- Use `.` between major fields and `: ` before pages.
- For Chinese output, use ASCII punctuation unless the user asks for full-width punctuation.
- Include DOI at the end as `https://doi.org/...` or `DOI: ...` if already provided that way.

## APA

Journal:

`Author, A. A., & Author, B. B. (Year). Title of article. Journal Title, Volume(Issue), pages. https://doi.org/...`

Thesis:

`Author, A. A. (Year). Title of thesis [Doctoral dissertation/Master's thesis, Institution]. Database or URL.`

Conference paper:

`Author, A. A. (Year, Month Day). Title of paper. In Proceedings/Conference Title (pp. pages). Publisher. DOI/URL.`

Book:

`Author, A. A. (Year). Title of book (Edition). Publisher. DOI/URL.`

Webpage:

`Author, A. A. (Year, Month Day). Title of page. Site Name. URL`

Notes:

- Use `n.d.` when no date exists and the user accepts placeholders; otherwise flag missing year.
- Use sentence case for article, thesis, chapter, and webpage titles when clear.
- Use italic styling in rich Markdown with `*Journal Title*`, `*Volume*`, and book/thesis titles when final output can use Markdown.

## MLA

Journal:

`Author(s). "Title of Article." Journal Title, vol. Volume, no. Issue, Year, pp. Pages. DOI/URL.`

Thesis:

`Author. Title of Thesis. Year. Institution, Degree thesis/dissertation.`

Conference paper:

`Author(s). "Title of Paper." Conference/Proceedings Title, Publisher, Year, pp. Pages.`

Book:

`Author(s). Title of Book. Edition, Publisher, Year.`

Webpage:

`Author(s). "Title of Page." Site Name, Publisher, Date, URL. Accessed Access Date.`

Notes:

- Put article, chapter, paper, and webpage titles in quotation marks.
- Use `pp.` for page ranges.
- Prefer URL without `https://` only if the user specifically requests MLA handbook strict display conventions; otherwise keep full URL for usability.

## Chicago

Use bibliography form unless the user asks for notes.

Journal:

`Author(s). "Title of Article." Journal Title Volume, no. Issue (Year): Pages. https://doi.org/....`

Thesis:

`Author. "Title of Thesis." Degree diss./thesis, Institution, Year.`

Conference paper:

`Author(s). "Title of Paper." In Proceedings Title, pages. Place: Publisher, Year.`

Book:

`Author(s). Title of Book. Edition. Place: Publisher, Year.`

Webpage:

`Author(s). "Title of Page." Site Name. Published/updated Date. URL.`

Notes:

- Use quotation marks for article, paper, thesis, and webpage titles.
- Use italics for journal titles, book titles, and proceedings titles when Markdown is acceptable.
- Include access date for undated or unstable web sources when provided.
