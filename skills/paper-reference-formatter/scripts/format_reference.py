#!/usr/bin/env python3
"""Format structured reference metadata into common citation styles."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


TYPE_MARKERS = {
    "journal": "J",
    "thesis": "D",
    "conference": "C",
    "book": "M",
    "report": "R",
    "preprint": "J",
    "webpage": "EB/OL",
}


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().strip(".")


def authors_list(ref: dict[str, Any]) -> list[str]:
    authors = ref.get("authors") or ref.get("author") or []
    if isinstance(authors, str):
        parts = re.split(r"\s*(?:;|, and | and |\|)\s*", authors)
        return [p.strip() for p in parts if p.strip()]
    return [clean(a) for a in authors if clean(a)]


def join_authors_plain(authors: list[str]) -> str:
    return ", ".join(authors) if authors else "[missing: author]"


def initials(given: str) -> str:
    parts = [p for p in re.split(r"[\s-]+", given.strip()) if p]
    return " ".join(f"{p[0].upper()}." for p in parts)


def apa_name(name: str) -> str:
    if "," in name:
        family, given = [p.strip() for p in name.split(",", 1)]
        return f"{family}, {initials(given)}" if given else family
    parts = name.split()
    if len(parts) >= 2 and all(ord(ch) < 128 for ch in name):
        return f"{parts[-1]}, {initials(' '.join(parts[:-1]))}"
    return name


def join_authors_apa(authors: list[str]) -> str:
    if not authors:
        return "[missing: author]"
    names = [apa_name(a) for a in authors]
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]}, & {names[1]}"
    return f"{', '.join(names[:-1])}, & {names[-1]}"


def normalize_doi(ref: dict[str, Any]) -> str:
    doi = clean(ref.get("doi"))
    if not doi:
        return ""
    doi = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", doi, flags=re.I)
    return f"https://doi.org/{doi}"


def pages(ref: dict[str, Any]) -> str:
    return clean(ref.get("pages") or ref.get("page"))


def year(ref: dict[str, Any]) -> str:
    return clean(ref.get("year") or ref.get("date") or ref.get("published"))


def gbt7714(ref: dict[str, Any]) -> str:
    typ = clean(ref.get("type")).lower() or "journal"
    marker = TYPE_MARKERS.get(typ, "J")
    authors = join_authors_plain(authors_list(ref))
    title = clean(ref.get("title")) or "[missing: title]"
    yr = year(ref) or "[missing: year]"
    container = clean(ref.get("container") or ref.get("journal") or ref.get("booktitle"))
    vol = clean(ref.get("volume"))
    issue = clean(ref.get("issue") or ref.get("number"))
    pg = pages(ref)
    place = clean(ref.get("place"))
    publisher = clean(ref.get("publisher"))
    institution = clean(ref.get("institution") or ref.get("school") or ref.get("university"))
    doi = normalize_doi(ref) or clean(ref.get("url"))

    if typ == "thesis":
        tail = f"{place}: {institution}, {yr}" if place else f"{institution}, {yr}"
        return finish(f"{authors}. {title}[D]. {tail}", doi)
    if typ == "book":
        edition = clean(ref.get("edition"))
        bits = [f"{authors}. {title}[M]"]
        if edition:
            bits.append(edition)
        pub = f"{place}: {publisher}, {yr}" if place else f"{publisher}, {yr}"
        bits.append(pub)
        return finish(". ".join(bits), doi)
    if typ == "conference":
        proc = container or "[missing: proceedings]"
        pub = f"{place}: {publisher}, {yr}" if publisher else yr
        page_part = f": {pg}" if pg else ""
        return finish(f"{authors}. {title}[C]//{proc}. {pub}{page_part}", doi)
    if typ in {"webpage", "web"}:
        accessed = clean(ref.get("accessed"))
        date = year(ref)
        access = f"[{accessed}]" if accessed else ""
        url = clean(ref.get("url"))
        return f"{authors}. {title}[EB/OL]. ({date}){access}. {url}."

    vol_issue = vol + (f"({issue})" if issue else "")
    loc = f"{container}, {yr}"
    if vol_issue:
        loc += f", {vol_issue}"
    if pg:
        loc += f": {pg}"
    return finish(f"{authors}. {title}[{marker}]. {loc}", doi)


def apa(ref: dict[str, Any]) -> str:
    typ = clean(ref.get("type")).lower() or "journal"
    authors = join_authors_apa(authors_list(ref))
    yr = year(ref) or "n.d."
    title = clean(ref.get("title")) or "[missing: title]"
    container = clean(ref.get("container") or ref.get("journal") or ref.get("booktitle"))
    doi = normalize_doi(ref) or clean(ref.get("url"))

    if typ == "thesis":
        degree = clean(ref.get("degree")) or "Thesis"
        institution = clean(ref.get("institution") or ref.get("school") or ref.get("university"))
        return finish(f"{authors} ({yr}). {title} [{degree}, {institution}]", doi)
    if typ == "book":
        publisher = clean(ref.get("publisher"))
        edition = clean(ref.get("edition"))
        ed = f" ({edition})" if edition else ""
        return finish(f"{authors} ({yr}). {title}{ed}. {publisher}", doi)
    if typ == "conference":
        pg = pages(ref)
        page_part = f" (pp. {pg})" if pg else ""
        publisher = clean(ref.get("publisher"))
        return finish(f"{authors} ({yr}). {title}. In {container}{page_part}. {publisher}", doi)
    if typ in {"webpage", "web"}:
        site = container or clean(ref.get("site"))
        return finish(f"{authors} ({yr}). {title}. {site}", doi)

    vol = clean(ref.get("volume"))
    issue = clean(ref.get("issue") or ref.get("number"))
    pg = pages(ref)
    vol_issue = vol + (f"({issue})" if issue else "")
    page_part = f", {pg}" if pg else ""
    return finish(f"{authors} ({yr}). {title}. {container}, {vol_issue}{page_part}", doi)


def mla(ref: dict[str, Any]) -> str:
    typ = clean(ref.get("type")).lower() or "journal"
    authors = join_authors_plain(authors_list(ref))
    yr = year(ref) or "[missing: year]"
    title = clean(ref.get("title")) or "[missing: title]"
    container = clean(ref.get("container") or ref.get("journal") or ref.get("booktitle"))
    doi = normalize_doi(ref) or clean(ref.get("url"))

    if typ == "book":
        edition = clean(ref.get("edition"))
        publisher = clean(ref.get("publisher"))
        ed = f"{edition}, " if edition else ""
        return finish(f"{authors}. {title}. {ed}{publisher}, {yr}", doi)
    if typ == "thesis":
        institution = clean(ref.get("institution") or ref.get("school") or ref.get("university"))
        degree = clean(ref.get("degree")) or "Thesis"
        return finish(f"{authors}. {title}. {yr}. {institution}, {degree}", doi)

    pg = pages(ref)
    page_part = f", pp. {pg}" if pg else ""
    vol = clean(ref.get("volume"))
    issue = clean(ref.get("issue") or ref.get("number"))
    vi = f", vol. {vol}" if vol else ""
    vi += f", no. {issue}" if issue else ""
    return finish(f'{authors}. "{title}." {container}{vi}, {yr}{page_part}', doi)


def chicago(ref: dict[str, Any]) -> str:
    typ = clean(ref.get("type")).lower() or "journal"
    authors = join_authors_plain(authors_list(ref))
    yr = year(ref) or "[missing: year]"
    title = clean(ref.get("title")) or "[missing: title]"
    container = clean(ref.get("container") or ref.get("journal") or ref.get("booktitle"))
    doi = normalize_doi(ref) or clean(ref.get("url"))

    if typ == "book":
        place = clean(ref.get("place"))
        publisher = clean(ref.get("publisher"))
        pub = f"{place}: {publisher}" if place else publisher
        return finish(f"{authors}. {title}. {pub}, {yr}", doi)
    if typ == "thesis":
        institution = clean(ref.get("institution") or ref.get("school") or ref.get("university"))
        degree = clean(ref.get("degree")) or "thesis"
        return finish(f'{authors}. "{title}." {degree}, {institution}, {yr}', doi)

    vol = clean(ref.get("volume"))
    issue = clean(ref.get("issue") or ref.get("number"))
    pg = pages(ref)
    vi = f" {vol}" if vol else ""
    vi += f", no. {issue}" if issue else ""
    page_part = f": {pg}" if pg else ""
    return finish(f'{authors}. "{title}." {container}{vi} ({yr}){page_part}', doi)


def finish(text: str, suffix: str = "") -> str:
    text = re.sub(r"\s+", " ", text).strip(" ,.")
    if suffix:
        return f"{text}. {suffix}."
    return f"{text}."


FORMATTERS = {
    "gbt7714": gbt7714,
    "gb/t7714": gbt7714,
    "gb/t 7714": gbt7714,
    "apa": apa,
    "mla": mla,
    "chicago": chicago,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--style", required=True, help="gbt7714, apa, mla, or chicago")
    parser.add_argument("--input", required=True, help="JSON file containing one reference or a list")
    args = parser.parse_args()

    style = args.style.lower()
    if style not in FORMATTERS:
        raise SystemExit(f"Unsupported style: {args.style}")

    data = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
    refs = data if isinstance(data, list) else [data]
    for i, ref in enumerate(refs, 1):
        print(f"{i}. {FORMATTERS[style](ref)}")


if __name__ == "__main__":
    main()
