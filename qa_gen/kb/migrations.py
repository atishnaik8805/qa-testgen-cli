# V2 ONLY — not used in v1 (flat-file KB)
# Restore in v2 when upgrading to Supabase + pgvector backend.
# Run via: qa-gen db init

import sys

import psycopg2

_DDL = [
    "CREATE EXTENSION IF NOT EXISTS vector",
    """
CREATE TABLE IF NOT EXISTS forms (
    id            UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    form_id       TEXT    UNIQUE NOT NULL,
    display_name  TEXT,
    module        TEXT,
    save_behavior TEXT    NOT NULL,
    save_trigger  TEXT    NOT NULL,
    parent_form_id TEXT   REFERENCES forms(form_id),
    content       TEXT    NOT NULL,
    embedding     VECTOR(1024),
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
)
""",
    """
CREATE TABLE IF NOT EXISTS components (
    id                  UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    component_id        TEXT    UNIQUE NOT NULL,
    label               TEXT    NOT NULL,
    description         TEXT    NOT NULL,
    interaction_steps   TEXT[]  NOT NULL,
    save_behavior_notes TEXT,
    forms               TEXT[],
    content             TEXT    NOT NULL,
    embedding           VECTOR(1024),
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
)
""",
    """
CREATE TABLE IF NOT EXISTS aliases (
    id          UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    phrase      TEXT    NOT NULL,
    target_id   TEXT    NOT NULL,
    target_type TEXT    NOT NULL CHECK (target_type IN ('form', 'component')),
    created_at  TIMESTAMPTZ DEFAULT NOW()
)
""",
    "CREATE UNIQUE INDEX IF NOT EXISTS aliases_phrase_idx ON aliases (phrase)",
    "CREATE INDEX IF NOT EXISTS forms_embedding_idx ON forms USING ivfflat (embedding vector_cosine_ops)",
    "CREATE INDEX IF NOT EXISTS forms_form_id_idx ON forms (form_id)",
    "CREATE INDEX IF NOT EXISTS components_embedding_idx ON components USING ivfflat (embedding vector_cosine_ops)",
    "CREATE INDEX IF NOT EXISTS components_id_idx ON components (component_id)",
    """
CREATE OR REPLACE FUNCTION match_forms(
    query_embedding VECTOR(1024),
    match_threshold FLOAT,
    match_count     INT
)
RETURNS TABLE(form_id TEXT, display_name TEXT, save_behavior TEXT, content TEXT, similarity FLOAT)
LANGUAGE SQL STABLE AS $$
    SELECT
        form_id,
        display_name,
        save_behavior,
        content,
        1 - (embedding <=> query_embedding) AS similarity
    FROM forms
    WHERE 1 - (embedding <=> query_embedding) > match_threshold
    ORDER BY similarity DESC
    LIMIT match_count;
$$
""",
    """
CREATE OR REPLACE FUNCTION match_components(
    query_embedding VECTOR(1024),
    match_threshold FLOAT,
    match_count     INT
)
RETURNS TABLE(component_id TEXT, label TEXT, description TEXT, similarity FLOAT)
LANGUAGE SQL STABLE AS $$
    SELECT
        component_id,
        label,
        description,
        1 - (embedding <=> query_embedding) AS similarity
    FROM components
    WHERE 1 - (embedding <=> query_embedding) > match_threshold
    ORDER BY similarity DESC
    LIMIT match_count;
$$
""",
]

_LABELS = [
    "CREATE EXTENSION vector",
    "CREATE TABLE forms",
    "CREATE TABLE components",
    "CREATE TABLE aliases",
    "CREATE UNIQUE INDEX aliases_phrase_idx",
    "CREATE INDEX forms_embedding_idx",
    "CREATE INDEX forms_form_id_idx",
    "CREATE INDEX components_embedding_idx",
    "CREATE INDEX components_id_idx",
    "CREATE FUNCTION match_forms",
    "CREATE FUNCTION match_components",
]


def run_migrations(db_url: str) -> None:
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
    except psycopg2.OperationalError as e:
        print(f"DB connection error: {e}", file=sys.stderr)
        raise SystemExit(2)

    with conn:
        cur = conn.cursor()
        for label, ddl in zip(_LABELS, _DDL):
            try:
                cur.execute(ddl)
                print(f"  ✓ {label}")
            except Exception as e:
                print(f"  ✗ {label}: {e}", file=sys.stderr)
                raise SystemExit(2)
        cur.close()
    conn.close()
