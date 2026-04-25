# V2 ONLY — not used in v1 (flat-file KB)
# Restore in v2 when upgrading to Supabase + pgvector backend.

import sys

import supabase
from supabase import Client

from qa_gen.config.settings import Settings


def create_supabase_client(settings: Settings) -> Client:
    return supabase.create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


def _guard(result):
    return result.data


def _check_tables(fn):
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            msg = str(e)
            if "relation" in msg and "does not exist" in msg:
                print(
                    "required tables are missing — run qa-gen db init",
                    file=sys.stderr,
                )
                raise SystemExit(2)
            raise
    return wrapper


@_check_tables
def get_form(client: Client, form_id: str) -> dict | None:
    result = client.table("forms").select("*").eq("form_id", form_id).execute()
    rows = result.data
    return rows[0] if rows else None


@_check_tables
def upsert_form(client: Client, data: dict) -> None:
    client.table("forms").upsert(data).execute()


@_check_tables
def list_forms(client: Client) -> list[dict]:
    return _guard(client.table("forms").select("form_id,display_name,save_behavior,module").execute())


@_check_tables
def get_component(client: Client, component_id: str) -> dict | None:
    result = client.table("components").select("*").eq("component_id", component_id).execute()
    rows = result.data
    return rows[0] if rows else None


@_check_tables
def upsert_component(client: Client, data: dict) -> None:
    client.table("components").upsert(data).execute()


@_check_tables
def list_components(client: Client) -> list[dict]:
    return _guard(
        client.table("components").select("component_id,label,forms").execute()
    )


@_check_tables
def get_alias(client: Client, phrase: str) -> dict | None:
    result = client.table("aliases").select("*").eq("phrase", phrase).execute()
    rows = result.data
    return rows[0] if rows else None


@_check_tables
def upsert_alias(client: Client, data: dict) -> None:
    client.table("aliases").upsert(data, on_conflict="phrase").execute()


@_check_tables
def delete_alias(client: Client, phrase: str) -> bool:
    result = client.table("aliases").delete().eq("phrase", phrase).execute()
    return bool(result.data)


@_check_tables
def list_aliases(
    client: Client,
    target_id: str | None = None,
    target_type: str | None = None,
) -> list[dict]:
    q = client.table("aliases").select("*")
    if target_id:
        q = q.eq("target_id", target_id)
    if target_type:
        q = q.eq("target_type", target_type)
    return _guard(q.execute())


@_check_tables
def match_forms(
    client: Client,
    query_embedding: list[float],
    threshold: float,
    count: int,
) -> list[dict]:
    return _guard(
        client.rpc(
            "match_forms",
            {"query_embedding": query_embedding, "match_threshold": threshold, "match_count": count},
        ).execute()
    )


@_check_tables
def match_components(
    client: Client,
    query_embedding: list[float],
    threshold: float,
    count: int,
) -> list[dict]:
    return _guard(
        client.rpc(
            "match_components",
            {"query_embedding": query_embedding, "match_threshold": threshold, "match_count": count},
        ).execute()
    )
