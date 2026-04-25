import os
import sys
from dataclasses import dataclass
from pathlib import Path


CONFIG_PATH = Path.home() / ".qa-gen" / ".env"


@dataclass
class Settings:
    JIRA_BASE_URL: str
    JIRA_EMAIL: str
    JIRA_API_TOKEN: str
    AI_PROVIDER: str
    AI_API_KEY: str
    AI_MODEL_NAME: str
    KB_PATH: Path
    # V2:
    # SUPABASE_URL: str
    # SUPABASE_SERVICE_KEY: str
    # SUPABASE_DB_URL: str | None
    # VOYAGE_API_KEY: str


def load_settings() -> Settings:
    if not CONFIG_PATH.exists():
        print("run qa-gen config first", file=sys.stderr)
        raise SystemExit(1)

    mode = os.stat(CONFIG_PATH).st_mode & 0o777
    if mode != 0o600:
        print(
            f"warning: ~/.qa-gen/.env permissions are {oct(mode)} — should be 0o600",
            file=sys.stderr,
        )

    env: dict[str, str] = {}
    with open(CONFIG_PATH) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            env[key.strip()] = val.strip()

    required = [
        "JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN",
        "AI_PROVIDER", "AI_API_KEY", "AI_MODEL_NAME",
    ]
    # V2: "SUPABASE_URL", "SUPABASE_SERVICE_KEY", "VOYAGE_API_KEY"
    missing = [k for k in required if k not in env]
    if missing:
        print(f"run qa-gen config first (missing: {', '.join(missing)})", file=sys.stderr)
        raise SystemExit(1)

    kb_path = Path(env.get("KB_PATH", "./knowledge_base")).expanduser()

    return Settings(
        JIRA_BASE_URL=env["JIRA_BASE_URL"],
        JIRA_EMAIL=env["JIRA_EMAIL"],
        JIRA_API_TOKEN=env["JIRA_API_TOKEN"],
        AI_PROVIDER=env["AI_PROVIDER"],
        AI_API_KEY=env["AI_API_KEY"],
        AI_MODEL_NAME=env["AI_MODEL_NAME"],
        KB_PATH=kb_path,
        # V2:
        # SUPABASE_URL=env["SUPABASE_URL"],
        # SUPABASE_SERVICE_KEY=env["SUPABASE_SERVICE_KEY"],
        # SUPABASE_DB_URL=env.get("SUPABASE_DB_URL") or None,
        # VOYAGE_API_KEY=env["VOYAGE_API_KEY"],
    )
