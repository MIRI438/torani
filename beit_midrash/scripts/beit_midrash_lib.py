# -*- coding: utf-8 -*-
"""
beit_midrash_lib.py
--------------------
Thin data-access layer over the SQLite beit-midrash database. No text
content lives here - every source's content is passed in by the caller,
never generated or altered by this module.
"""

import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "db" / "schema.sql"


def connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(conn):
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()


def _get_or_create(conn, table, name, extra_cols=None):
    row = conn.execute(f"SELECT id FROM {table} WHERE name = ?", (name,)).fetchone()
    if row:
        return row["id"]
    cols = ["name"]
    vals = [name]
    if extra_cols:
        cols += list(extra_cols.keys())
        vals += list(extra_cols.values())
    placeholders = ", ".join("?" * len(vals))
    cur = conn.execute(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})", vals)
    conn.commit()
    return cur.lastrowid


def add_layer(conn, name, order_rank):
    row = conn.execute("SELECT id FROM layers WHERE name = ?", (name,)).fetchone()
    if row:
        return row["id"]
    cur = conn.execute("INSERT INTO layers (name, order_rank) VALUES (?, ?)", (name, order_rank))
    conn.commit()
    return cur.lastrowid


def add_face(conn, name):
    return _get_or_create(conn, "faces", name)


def add_genre(conn, name):
    return _get_or_create(conn, "genres", name)


def add_relation_type(conn, name):
    return _get_or_create(conn, "relation_types", name)


def add_sugya(conn, name):
    return _get_or_create(conn, "sugyot", name)


def get_layer(conn, name):
    row = conn.execute("SELECT * FROM layers WHERE name = ?", (name,)).fetchone()
    if not row:
        raise ValueError(f"unknown layer: {name!r}")
    return row


def _check_hierarchy(conn, layer_row):
    """Every layer with a lower order_rank must already contain at least one source."""
    lower_layers = conn.execute(
        "SELECT id, name FROM layers WHERE order_rank < ? ORDER BY order_rank",
        (layer_row["order_rank"],),
    ).fetchall()
    empty = []
    for lyr in lower_layers:
        count = conn.execute(
            "SELECT COUNT(*) AS c FROM sources WHERE layer_id = ?", (lyr["id"],)
        ).fetchone()["c"]
        if count == 0:
            empty.append(lyr["name"])
    if empty:
        raise ValueError(
            f"hierarchy violation: layer(s) {empty} are still empty, "
            f"cannot add to a later layer without enforce_hierarchy=False"
        )


def add_source(
    conn,
    content,
    layer,
    reference=None,
    language=None,
    era=None,
    faces=None,
    genres=None,
    sugyot=None,
    enforce_hierarchy=True,
):
    layer_row = get_layer(conn, layer)
    if enforce_hierarchy:
        _check_hierarchy(conn, layer_row)

    cur = conn.execute(
        "INSERT INTO sources (reference, content, layer_id, language, era) "
        "VALUES (?, ?, ?, ?, ?)",
        (reference, content, layer_row["id"], language, era),
    )
    source_id = cur.lastrowid

    for face in faces or []:
        face_id = add_face(conn, face)
        conn.execute(
            "INSERT OR IGNORE INTO source_faces (source_id, face_id) VALUES (?, ?)",
            (source_id, face_id),
        )
    for genre in genres or []:
        genre_id = add_genre(conn, genre)
        conn.execute(
            "INSERT OR IGNORE INTO source_genres (source_id, genre_id) VALUES (?, ?)",
            (source_id, genre_id),
        )
    for sugya in sugyot or []:
        sugya_id = add_sugya(conn, sugya)
        conn.execute(
            "INSERT OR IGNORE INTO source_sugyot (source_id, sugya_id) VALUES (?, ?)",
            (source_id, sugya_id),
        )

    conn.commit()
    return source_id


def add_connection(conn, source_id, target_id, relation_type, note=None):
    relation_type_id = add_relation_type(conn, relation_type)
    cur = conn.execute(
        "INSERT INTO connections (source_id, target_id, relation_type_id, note) "
        "VALUES (?, ?, ?, ?)",
        (source_id, target_id, relation_type_id, note),
    )
    conn.commit()
    return cur.lastrowid
