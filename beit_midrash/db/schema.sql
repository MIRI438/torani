-- Beit Midrash schema
-- Core idea: SOURCES is the single table holding every text unit (verse, mishnah,
-- gemara passage, commentary, ...). Every other table tags SOURCES without
-- duplicating its content:
--   LAYERS   - one historical/authority layer per source (1-to-many), ordered by order_rank
--   FACES    - pardes reading (peshat/remez/drash/sod), many-to-many
--   GENRES   - literary genre (halacha/aggada/machshava/kabbalah...), many-to-many
--   CONNECTIONS - relations between two sources (self-referencing, "the glass prism")
--   SUGYOT   - topical groupings ("edim zomemim" etc.), many-to-many via SOURCE_SUGYOT

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS layers (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    order_rank  INTEGER NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS faces (
    id      INTEGER PRIMARY KEY,
    name    TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS genres (
    id      INTEGER PRIMARY KEY,
    name    TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS relation_types (
    id      INTEGER PRIMARY KEY,
    name    TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS sugyot (
    id      INTEGER PRIMARY KEY,
    name    TEXT NOT NULL UNIQUE
);

-- reference: citation only ("דברים יט, טו"), never interpretive.
-- embedding: reserved for future semantic search; unused for now.
CREATE TABLE IF NOT EXISTS sources (
    id          INTEGER PRIMARY KEY,
    reference   TEXT,
    content     TEXT NOT NULL,
    layer_id    INTEGER NOT NULL REFERENCES layers(id),
    language    TEXT,
    era         TEXT,
    embedding   BLOB,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS source_faces (
    source_id   INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    face_id     INTEGER NOT NULL REFERENCES faces(id),
    PRIMARY KEY (source_id, face_id)
);

CREATE TABLE IF NOT EXISTS source_genres (
    source_id   INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    genre_id    INTEGER NOT NULL REFERENCES genres(id),
    PRIMARY KEY (source_id, genre_id)
);

CREATE TABLE IF NOT EXISTS source_sugyot (
    source_id   INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    sugya_id    INTEGER NOT NULL REFERENCES sugyot(id),
    PRIMARY KEY (source_id, sugya_id)
);

CREATE TABLE IF NOT EXISTS connections (
    id                  INTEGER PRIMARY KEY,
    source_id           INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    target_id           INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    relation_type_id    INTEGER NOT NULL REFERENCES relation_types(id),
    note                TEXT
);

CREATE INDEX IF NOT EXISTS idx_sources_layer ON sources(layer_id);
CREATE INDEX IF NOT EXISTS idx_connections_source ON connections(source_id);
CREATE INDEX IF NOT EXISTS idx_connections_target ON connections(target_id);
