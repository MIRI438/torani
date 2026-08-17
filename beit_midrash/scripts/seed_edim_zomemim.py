# -*- coding: utf-8 -*-
"""
seed_edim_zomemim.py
---------------------
Seeds the beit-midrash database with the sugyat "edim zomemim" (Devarim 19,
15-21) content supplied so far: the 7 Torah verses and the 10 mishnayot of
Makkot perek alef. Text is taken verbatim from sources/raw/ - nothing is
retyped, paraphrased, or interpreted.

Tagging follows the decisions already made for this project:
  - Verses: layer=תנ"ך, face=פשט, genre=הלכה
  - Mishnayot: layer=משנה, face=פשט, genre=הלכה
  - Both tagged to the sugya "עדים זוממים"

Also seeded: Tosefta Makkot perek alef (6 halachot), sourced from the
Otzaria library (github.com/zevisvei/otzaria-library) - this fills the
Tosefta layer, which was previously empty and blocked hierarchy enforcement
for the Talmud layer.

Gemara (Bavli Makkot) and Rashi are staged as raw text under sources/raw/
but NOT yet split into atomic SOURCES rows: the Otzaria text shows 12
mishnah-transition markers ("מתני'") between daf 2a and 7b, but perek alef
has only 10 mishnayot, so the exact daf/amud where perek alef's Gemara ends
is not yet pinned down. Splitting now would risk mis-scoping which passages
belong to this sugya - left as a follow-up step, not guessed at here.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from beit_midrash_lib import connect, init_schema, add_layer, add_source  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "sources" / "raw"
DB_PATH = ROOT / "db" / "beit_midrash.sqlite"

LAYERS = [
    ("תנ\"ך", 1),
    ("תרגומים", 2),
    ("משנה", 3),
    ("תוספתא", 4),
    ("תלמוד", 5),
    ("גאונים", 6),
    ("ראשונים", 7),
    ("אחרונים", 8),
    ("פוסקים", 9),
]

SUGYA = "עדים זוממים"

VERSE_LETTERS = ["טו", "טז", "יז", "יח", "יט", "כ", "כא"]


def parse_verses(text):
    """Extract the (letter) verse lines between the 'הנה מצורף:' marker and
    the 'עד כאן הפסוקים' marker. Returns [(letter, verse_text), ...]."""
    start = text.index("הנה מצורף:") + len("הנה מצורף:")
    end = text.index("עד כאן הפסוקים")
    block = text[start:end]
    pattern = re.compile(r"\((" + "|".join(VERSE_LETTERS) + r")\)\s*(.*?)(?=\(\s*(?:" + "|".join(VERSE_LETTERS) + r")\s*\)|$)", re.S)
    verses = []
    for m in pattern.finditer(block):
        letter = m.group(1)
        verse = m.group(2).strip()
        verse = re.sub(r"\s+", " ", verse)
        verses.append((letter, verse))
    return verses


def parse_targum(text):
    pattern = re.compile(r"\((" + "|".join(VERSE_LETTERS) + r")\)\s*(.*?)(?=\(\s*(?:" + "|".join(VERSE_LETTERS) + r")\s*\)|$)", re.S)
    out = []
    for m in pattern.finditer(text):
        verse = re.sub(r"\s+", " ", m.group(2).strip())
        out.append((m.group(1), verse))
    return out


def parse_tosefta(text):
    pattern = re.compile(r"\(([א-ת]{1,3})\)\s*(.*?)(?=\([א-ת]{1,3}\)|$)", re.S)
    halachot = []
    for m in pattern.finditer(text):
        letter = m.group(1)
        body = m.group(2).strip()
        body = re.sub(r"\s+", " ", body)
        if body:
            halachot.append((letter, body))
    return halachot


def parse_mishnayot(text):
    """Split on (letter) markers, dropping the stray page-break headers
    'משנה מכות' and 'פרק א' that appear mid-text in the source dump."""
    cleaned = text.replace("משנה מכות", "").replace("פרק א", "")
    pattern = re.compile(r"\(([א-ת]{1,3})\)\s*(.*?)(?=\([א-ת]{1,3}\)|$)", re.S)
    mishnayot = []
    for m in pattern.finditer(cleaned):
        letter = m.group(1)
        body = m.group(2).strip()
        body = re.sub(r"\s+", " ", body)
        if body:
            mishnayot.append((letter, body))
    return mishnayot


def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(DB_PATH)
    init_schema(conn)

    for name, rank in LAYERS:
        add_layer(conn, name, rank)

    verses_text = (RAW / "torah_devarim_19_15-21_edim_zomemim.txt").read_text(encoding="utf-8")
    verses = parse_verses(verses_text)
    assert len(verses) == 7, f"expected 7 verses, got {len(verses)}"
    for letter, verse in verses:
        add_source(
            conn,
            content=verse,
            layer="תנ\"ך",
            reference=f"דברים יט, {letter}",
            language="עברית",
            faces=["פשט"],
            genres=["הלכה"],
            sugyot=[SUGYA],
            enforce_hierarchy=True,
        )
    print(f"inserted {len(verses)} verses (Devarim 19:15-21)")

    for targum_name, filename in [
        ("תרגום אונקלוס", "targum_onkelos_devarim_19_otzaria.txt"),
        ("תרגום יונתן", "targum_yonatan_devarim_19_otzaria.txt"),
    ]:
        targum_text = (RAW / filename).read_text(encoding="utf-8")
        targum_verses = parse_targum(targum_text)
        assert len(targum_verses) == 7, f"expected 7 {targum_name} verses, got {len(targum_verses)}"
        for letter, verse in targum_verses:
            add_source(
                conn,
                content=verse,
                layer="תרגומים",
                reference=f"{targum_name}, דברים יט, {letter}",
                language="ארמית",
                faces=["פשט"],
                genres=["הלכה"],
                sugyot=[SUGYA],
                enforce_hierarchy=True,
            )
        print(f"inserted {len(targum_verses)} verses ({targum_name})")

    mishnah_text = (RAW / "mishnah_makkot_perek_1_edim_zomemim.txt").read_text(encoding="utf-8")
    mishnayot = parse_mishnayot(mishnah_text)
    assert len(mishnayot) == 10, f"expected 10 mishnayot, got {len(mishnayot)}"
    for letter, body in mishnayot:
        add_source(
            conn,
            content=body,
            layer="משנה",
            reference=f"משנה מכות א, {letter}",
            language="עברית",
            faces=["פשט"],
            genres=["הלכה"],
            sugyot=[SUGYA],
            enforce_hierarchy=True,
        )
    print(f"inserted {len(mishnayot)} mishnayot (Makkot 1)")

    tosefta_text = (RAW / "tosefta_makkot_perek_1_edim_zomemim.txt").read_text(encoding="utf-8")
    halachot = parse_tosefta(tosefta_text)
    assert len(halachot) == 6, f"expected 6 tosefta halachot, got {len(halachot)}"
    for letter, body in halachot:
        add_source(
            conn,
            content=body,
            layer="תוספתא",
            reference=f"תוספתא מכות א, {letter}",
            language="עברית",
            faces=["פשט"],
            genres=["הלכה"],
            sugyot=[SUGYA],
            enforce_hierarchy=True,
        )
    print(f"inserted {len(halachot)} tosefta halachot (Makkot 1)")

    total = conn.execute("SELECT COUNT(*) AS c FROM sources").fetchone()["c"]
    print(f"total sources in db: {total}")
    conn.close()


if __name__ == "__main__":
    main()
