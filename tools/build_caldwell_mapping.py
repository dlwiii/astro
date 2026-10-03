#!/usr/bin/env python3
"""Build the Caldwell -> NGC/IC cross-reference (targets/caldwell.json + targets/CALDWELL.md).

Primary source   : Wikipedia "Caldwell catalogue" (table parsed from raw wikitext).
Cross-check      : SEDS Caldwell list (independent transcription of Moore's original list).

Both sources are fetched live; every row is diffed between them and any disagreement that is
not a known, documented erratum aborts the build. Re-run after editing CORRECTIONS/NOTES.

    python3 scripts/build_caldwell_mapping.py
"""
import json
import re
import sys
import urllib.request
from datetime import date
from html import unescape
import os
from pathlib import Path

WIKI = "https://en.wikipedia.org/w/index.php?title=Caldwell_catalogue&action=raw"
SEDS = "http://www.messier.seds.org/xtra/similar/caldwell.html"

def _find_astro_root():
    """Walk up from this file to the directory holding sessions/ and targets/.

    Works whether the script runs from ~/astro/scripts (a symlink) or from its
    real home in the gallery repo's tools/ folder. ASTRO_DIR env var overrides.
    """
    env = os.environ.get("ASTRO_DIR")
    if env:
        return Path(env)
    for p in Path(__file__).resolve().parents:
        if (p / "sessions").is_dir() and (p / "targets").is_dir():
            return p
    return Path.home() / "astro"

OUT = _find_astro_root() / "targets"
UA = {"User-Agent": "astro-catalog-build/1.0 (personal astrophotography catalog)"}

# ---------------------------------------------------------------- corrections
# Additional NGC numbers covering the same physical object, not part of Moore's designation.
ALSO = {
    33: ["NGC 6995"],                          # SEDS writes "NGC 6992/5"; CATALOG.md agrees
    49: ["NGC 2238", "NGC 2239", "NGC 2246"],  # SEDS writes "NGC 2237-9"; 2246 from CATALOG.md
}
NOTES = {
    9:   "No NGC/IC number; Sharpless designation only.",
    14:  "Two NGC objects under one Caldwell number (h and chi Persei).",
    26:  "Listed out of declination sequence in Moore's original list.",
    33:  "East Veil; NGC 6995 is the same filament complex. NGC 6960 (C34) is the West Veil.",
    41:  "No NGC/IC number; Melotte 25 (also catalogued as Collinder 50). Listed out of "
         "declination sequence in Moore's original list.",
    49:  "The nebula itself; C50 (NGC 2244) is the cluster embedded in it.",
    50:  "The embedded cluster; C49 (NGC 2237) is the surrounding nebula.",
    89:  "Moore's original list gave NGC 6067 in error; the S Normae Cluster is NGC 6087. "
         "SEDS still reproduces the original error.",
    99:  "No NGC, IC or other catalogue number - a naked-eye dark nebula.",
    100: "Moore's original list labelled this the Gamma Centauri Cluster in error; "
         "IC 2944 is the Lambda Centauri Cluster.",
}
# Caldwell numbers where SEDS is expected to disagree with Wikipedia, with the reason.
EXPECTED_DIFFS = {
    89: "SEDS reproduces Moore's original NGC 6067 error; correct object is NGC 6087.",
}


def fetch(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read()


# ---------------------------------------------------------------- wikitext parsing
ATTR_RE = re.compile(r'^\s*(?:[a-zA-Z-]+\s*=\s*"[^"]*"\s*)+\|(?!\|)')
DESIG_RE = re.compile(r"\b(NGC|IC|Mel|Melotte|Cr|Collinder|Sh2|Tr|Stock)[\s -]*([0-9]+)", re.I)
CANON = {"ngc": "NGC", "ic": "IC", "mel": "Mel", "melotte": "Mel",
         "cr": "Cr", "collinder": "Cr", "sh2": "Sh2", "tr": "Tr", "stock": "Stock"}


def clean(s):
    """A wikitext table cell -> plain text, keeping link display text."""
    while ATTR_RE.search(s):                       # style="..."| prefixes, sometimes on own line
        s = ATTR_RE.sub("", s, count=1)
    s = re.sub(r"\[\[(?:File|Image):[^\]]*\]\]", " ", s)
    s = re.sub(r"<ref[^>]*/>", "", s)
    s = re.sub(r"<ref.*?</ref>", "", s, flags=re.DOTALL)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\{\{hs\|\d+\}\}", "", s)
    s = re.sub(r"\{\{[^}]*\}\}", "", s)
    s = re.sub(r"\[\[([^\]\|]+)\|([^\]]+)\]\]", r"\2", s)   # [[target|display]] -> display
    s = re.sub(r"\[\[([^\]]+)\]\]", r"\1", s)               # [[target]]         -> target
    s = s.replace("&nbsp;", " ").replace("&amp;", "&").replace("''", "")
    return re.sub(r"\s+", " ", s).strip()


def split_designations(text):
    ngc, ic, other = [], [], []
    for m in DESIG_RE.finditer(text):
        prefix = CANON[m.group(1).lower()]
        tag = f"Sh2-{m.group(2)}" if prefix == "Sh2" else f"{prefix} {m.group(2)}"
        (ngc if prefix == "NGC" else ic if prefix == "IC" else other).append(tag)
    dedup = lambda xs: list(dict.fromkeys(xs))
    return dedup(ngc), dedup(ic), dedup(other)


def parse_wikipedia(text):
    lines = text.splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith('{| class="wikitable sortable"'))
    end = next(i for i in range(start, len(lines)) if lines[i].strip() == "|}")

    rows, cur = [], None
    for line in lines[start + 1:end]:
        if line.startswith("|-"):
            if cur:
                rows.append(cur)
            cur = []
        elif cur is not None:
            cur.append(line)
    if cur:
        rows.append(cur)

    out = {}
    for row in rows:
        cells = []
        for line in row:                            # group continuation lines with their cell
            if line.startswith("|") and not line.startswith("|-"):
                cells.append(line[1:])
            elif cells:
                cells[-1] += " " + line
        if len(cells) < 8:
            continue
        m = re.match(r"C(\d+)$", clean(cells[0]))
        if not m:
            continue
        n = int(m.group(1))
        ngc, ic, other = split_designations(clean(cells[1]))
        name, otype, dist, const, mag = (clean(cells[i]) for i in (2, 4, 5, 6, 7))
        out[n] = {
            "caldwell": f"C{n}", "number": n,
            "ngc": ngc, "ic": ic, "other_designations": other,
            "also_designated": ALSO.get(n, []),
            "primary_designation": (ngc + ic + other or [None])[0],
            "common_name": name if name and name != "-" else None,
            "type": otype,
            "constellation": const,
            "distance_kly": float(dist.replace(",", "")) if re.fullmatch(r"[\d,.]+", dist) else None,
            "magnitude": float(mag) if re.fullmatch(r"-?[\d.]+", mag) else None,
        }
        if n in NOTES:
            out[n]["note"] = NOTES[n]
    return out


def parse_seds(html_text):
    """SEDS rows look like '  5 =  IC  342' / ' 14 = NGC  869/884, Double Cluster'."""
    text = unescape(re.sub(r"<[^>]*>", "", html_text))
    rows = {}
    for m in re.finditer(r"^\s*(\d{1,3}) = (.+)$", text, re.M):
        n = int(m.group(1))
        if 1 <= n <= 109:
            rows[n] = re.sub(r"\s+", " ", m.group(2)).strip()
    return rows


def seds_designations(n, raw):
    """Normalise a SEDS row to a designation set, expanding its 6992/5 and 2237-9 shorthands."""
    out = set()
    for m in re.finditer(r"(NGC|IC)\s+(\d+)((?:\s*[/-]\s*\d+)*)", raw):
        prefix, first, tail = m.group(1), m.group(2), m.group(3)
        out.add(f"{prefix} {first}")
        for part in re.findall(r"\d+", tail):
            full = first[:len(first) - len(part)] + part      # 6992/5 -> 6995, 2237-9 -> 2239
            lo, hi = int(first), int(full)
            span = range(lo, hi + 1) if "-" in tail and hi > lo else [hi]
            out.update(f"{prefix} {v}" for v in span)
    out.update(re.findall(r"Sh2-\d+", raw))
    if "Melotte 25" in raw:
        out.add("Mel 25")
    if n == 106:
        out.discard("NGC 47")                                 # "47 Tucanae" is a name, not an NGC
    return out


def cross_check(objects, seds):
    problems = []
    for n in range(1, 110):
        e = objects[n]
        mine = set(e["ngc"] + e["ic"] + e["other_designations"] + e["also_designated"])
        theirs = seds_designations(n, seds[n])
        theirs.discard("NGC 2246")                            # local-only addition from CATALOG.md
        mine.discard("NGC 2246")
        if mine != theirs and n not in EXPECTED_DIFFS:
            problems.append(f"C{n}: wikipedia={sorted(mine)} seds={sorted(theirs)} [{seds[n]}]")
    return problems


# ---------------------------------------------------------------- output
def wiki_cell(e):
    """Markdown link to the object's Wikipedia article, labelled with the article title."""
    url = e.get("wikipedia_url")
    if not url:
        return "—"
    label = url.rsplit("/", 1)[-1].split("#")[0].replace("_", " ")
    # A destination containing parentheses needs the <...> form to parse reliably.
    dest = f"<{url}>" if "(" in url or ")" in url else url
    return f"[{label}]({dest})"


def designation_str(e):
    d = e["ngc"] + e["ic"] + e["other_designations"]
    s = ", ".join(d) if d else "—"
    if e["also_designated"]:
        s += " (+ " + ", ".join(e["also_designated"]) + ")"
    return s


def table(header, aligns, rows, pad_last=True):
    """Pipe table, every pipe in the same raw column.

    pad_last=False leaves the final column unpadded - for a column of URLs, where padding
    to the longest cell adds a lot of trailing whitespace and aligns nothing useful.
    """
    widths = [max(len(str(r[i])) for r in [header] + rows) for i in range(len(header))]
    if not pad_last:
        widths[-1] = 0
    def fmt(cells, pad=" "):
        out = []
        for c, w, a in zip(cells, widths, aligns):
            out.append(str(c).rjust(w, pad) if a == "right" else str(c).ljust(w, pad))
        return "| " + " | ".join(out) + " |"
    sep = ["-" * max(w, 3) for w in widths]
    sep = [(s[:-1] + ":") if a == "right" else s for s, a in zip(sep, aligns)]
    return [fmt(header), "| " + " | ".join(sep) + " |"] + [fmt(r) for r in rows]


def write_markdown(objects, path):
    md = [
        "# Caldwell Catalog Cross-Reference", "",
        "Mapping of all 109 Caldwell objects (C1–C109) to their NGC, IC and other catalogue",
        "designations. The Caldwell catalogue was compiled by Patrick Moore as a complement to",
        "the Messier catalogue and is ordered by declination, C1 being the most northerly.",
        "No Caldwell object is also a Messier object.", "",
        "Machine-readable form, including a reverse designation → Caldwell index:",
        "[caldwell.json](caldwell.json). Regenerate both with",
        "`python3 scripts/build_caldwell_mapping.py`.", "",
        "**Sources:** [Caldwell catalogue — Wikipedia](https://en.wikipedia.org/wiki/Caldwell_catalogue)",
        "(primary), [SEDS Caldwell list](http://www.messier.seds.org/xtra/similar/caldwell.html)",
        "(independent cross-check). All 109 rows agree between the two sources except C89,",
        "noted below.", "", "---", "", "## Cross-reference table", "",
    ]
    md += table(
        ["Caldwell", "Designation(s)", "Common name", "Type", "Constellation", "Mag",
         "Wikipedia"],
        ["left", "left", "left", "left", "left", "right", "left"],
        [[e["caldwell"], designation_str(e), e["common_name"] or "—", e["type"],
          e["constellation"], f"{e['magnitude']:g}" if e["magnitude"] is not None else "—",
          wiki_cell(e)]
         for e in objects],
        pad_last=False)
    md += ["",
           "`(+ …)` marks additional NGC numbers that cover the same physical object but are not",
           "part of Moore's designation.", "", "---", "", "## Notes and known errata", ""]
    for e in objects:
        if "note" in e:
            label = designation_str(e)
            parts = [p for p in (label if label != "—" else None, e["common_name"]) if p]
            title = " — ".join(parts)
            md.append(f"- **{e['caldwell']}** ({title}): {e['note']}")
    md += ["", "---", "", "## Objects with no NGC or IC number", ""]
    md += table(["Caldwell", "Designation", "Common name", "Constellation"],
                ["left"] * 4,
                [[e["caldwell"], ", ".join(e["other_designations"]) or "—",
                  e["common_name"] or "—", e["constellation"]]
                 for e in objects if not e["ngc"] and not e["ic"]])
    md += ["", "## IC-only objects", ""]
    md += table(["Caldwell", "IC", "Common name", "Constellation"],
                ["left"] * 4,
                [[e["caldwell"], ", ".join(e["ic"]), e["common_name"] or "—", e["constellation"]]
                 for e in objects if e["ic"] and not e["ngc"]])
    md.append("")
    path.write_text("\n".join(md))


def main():
    wiki = parse_wikipedia(fetch(WIKI).decode("utf-8"))
    seds = parse_seds(fetch(SEDS).decode("latin-1"))

    missing = [n for n in range(1, 110) if n not in wiki]
    if missing or len(wiki) != 109:
        sys.exit(f"wikipedia parse produced {len(wiki)} rows, missing {missing}")
    if len(seds) != 109:
        sys.exit(f"seds parse produced {len(seds)} rows")

    problems = cross_check(wiki, seds)
    if problems:
        sys.exit("cross-check failed:\n  " + "\n  ".join(problems))

    objects = [wiki[n] for n in range(1, 110)]

    # Carry forward Wikipedia links so regenerating the mapping does not drop them;
    # scripts/fetch_caldwell_wikipedia_links.py is what produces them.
    existing = OUT / "caldwell.json"
    if existing.exists():
        prior = {e["number"]: e.get("wikipedia_url")
                 for e in json.loads(existing.read_text())["objects"]}
        for e in objects:
            if prior.get(e["number"]):
                e["wikipedia_url"] = prior[e["number"]]
        kept = sum(1 for e in objects if e.get("wikipedia_url"))
        if kept:
            print(f"  carried forward {kept} wikipedia_url values")
        if kept < len(objects):
            print("  note: some objects have no wikipedia_url - run "
                  "scripts/fetch_caldwell_wikipedia_links.py")
    reverse = {}
    for e in objects:
        for d in e["ngc"] + e["ic"] + e["other_designations"] + e["also_designated"]:
            reverse.setdefault(d, e["caldwell"])
            reverse.setdefault(d.replace(" ", ""), e["caldwell"])   # NGC188 / IC342 spellings

    doc = {
        "catalog": "Caldwell",
        "description": "Mapping of the 109 Caldwell objects to their NGC, IC and other catalogue "
                       "designations, with common name, type, constellation and magnitude.",
        "count": len(objects),
        "generated": date.today().isoformat(),
        "generator": "scripts/build_caldwell_mapping.py",
        "sources": [
            WIKI + "  (primary; table parsed from raw wikitext)",
            SEDS + "  (independent cross-check)",
            "targets/CATALOG.md  (local cross-check; sole source for NGC 2246 under C49)",
        ],
        "field_notes": {
            "ngc / ic / other_designations": "Designations Moore assigned to this entry; an empty "
                                             "list means the object has none in that catalogue.",
            "also_designated": "Extra NGC/IC numbers covering the same physical object, not part "
                               "of Moore's designation.",
            "primary_designation": "First designation; null for C99 (Coalsack), which has none.",
            "distance_kly": "Thousands of light years, per the Wikipedia table; null if unlisted.",
            "designation_to_caldwell": "Reverse index, including space-free spellings (NGC188).",
            "wikipedia_url": "Article resolved via the MediaWiki API and verified to name the "
                             "object; generated by scripts/fetch_caldwell_wikipedia_links.py.",
        },
        "objects": objects,
        "designation_to_caldwell": dict(sorted(reverse.items())),
    }
    (OUT / "caldwell.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    write_markdown(objects, OUT / "CALDWELL.md")
    print(f"ok: {len(objects)} objects, {len(reverse)} reverse keys, cross-check clean")
    print(f"  {OUT / 'caldwell.json'}")
    print(f"  {OUT / 'CALDWELL.md'}")


if __name__ == "__main__":
    main()
