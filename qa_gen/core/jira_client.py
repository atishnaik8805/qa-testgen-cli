import sys
import time

import httpx

from qa_gen.core.adf_parser import parse_adf

_RETRIES = 3
_BACKOFF = [1, 2, 4]
_FIELDS = "summary,description,customfield_10016,labels,components,subtasks,issuetype"


class JiraClient:
    def __init__(self, base_url: str, email: str, api_token: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._auth = httpx.BasicAuth(email, api_token)

    def fetch_story(self, story_id: str) -> dict:
        url = f"{self._base_url}/rest/api/3/issue/{story_id}"
        last_exc: Exception | None = None

        for attempt, delay in enumerate(_BACKOFF):
            try:
                resp = httpx.get(url, auth=self._auth, params={"fields": _FIELDS}, timeout=30)
                if resp.status_code == 404:
                    print(f"Story {story_id} not found in JIRA", file=sys.stderr)
                    raise SystemExit(2)
                if resp.status_code == 429:
                    try:
                        retry_after = int(resp.headers.get("Retry-After", 30))
                    except (ValueError, TypeError):
                        retry_after = 30
                    time.sleep(retry_after)
                    continue
                resp.raise_for_status()
                data = resp.json()
                fields = data.get("fields", {})
                fields["_parsed_description"] = parse_adf(fields.get("description"))
                fields["_parsed_acceptance_criteria"] = parse_adf(fields.get("customfield_10016"))
                data["fields"] = fields
                return data
            except SystemExit:
                raise
            except Exception as e:
                last_exc = e
                if attempt < _RETRIES - 1:
                    time.sleep(delay)

        print(f"JIRA request failed after {_RETRIES} attempts: {last_exc}", file=sys.stderr)
        raise SystemExit(2)
