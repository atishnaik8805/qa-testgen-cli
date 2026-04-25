import json
import sys
from pathlib import Path

from qa_gen.cli.display import confirm
from qa_gen.core.jira_client import JiraClient
from qa_gen.models.test_case import TestCase

_RETRIES = 3
_BACKOFF = [1, 2, 4]


def count_existing_qa_subtasks(story_id: str, jira_client: JiraClient) -> int:
    data = jira_client.fetch_story(story_id)
    subtasks = data.get("fields", {}).get("subtasks") or []
    count = 0
    for sub in subtasks:
        labels = sub.get("fields", {}).get("labels") or []
        if "qa-gen" in labels:
            count += 1
    return count


def create_subtasks(
    story_id: str,
    test_cases: list[TestCase],
    jira_client: JiraClient,
    no_confirm: bool = False,
) -> bool:
    existing = count_existing_qa_subtasks(story_id, jira_client)
    if existing:
        print(
            f"warning: {existing} existing qa-gen subtask(s) found on {story_id}",
            file=sys.stderr,
        )

    if not no_confirm:
        if not confirm(f"Push {len(test_cases)} test case(s) to JIRA as subtasks of {story_id}?"):
            return False

    import time
    base_url = jira_client._base_url
    created = []
    failed = []

    # Get project key from story_id
    project_key = story_id.split("-")[0]

    for tc in test_cases:
        payload = {
            "fields": {
                "project": {"key": project_key},
                "parent": {"key": story_id},
                "summary": tc.title,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": tc.to_gherkin_scenario()}],
                        }
                    ],
                },
                "issuetype": {"name": "Subtask"},
                "labels": ["auto-generated", "qa-gen"],
            }
        }

        import httpx
        last_exc: Exception | None = None
        for attempt, delay in enumerate(_BACKOFF):
            try:
                resp = httpx.post(
                    f"{base_url}/rest/api/3/issue",
                    auth=jira_client._auth,
                    json=payload,
                    timeout=30,
                )
                if resp.status_code == 429:
                    try:
                        retry_after = int(resp.headers.get("Retry-After", 30))
                    except (ValueError, TypeError):
                        retry_after = 30
                    time.sleep(retry_after)
                    continue
                resp.raise_for_status()
                created.append(tc.title)
                break
            except Exception as e:
                last_exc = e
                if attempt < _RETRIES - 1:
                    time.sleep(delay)
        else:
            failed.append((tc.title, last_exc))

    if failed:
        fallback_path = Path(f"test-cases-{story_id}.md")
        _write_md(fallback_path, test_cases)
        print(
            f"Some subtasks failed to create. Saved all to {fallback_path}",
            file=sys.stderr,
        )
        for title, exc in failed:
            print(f"  failed: {title!r}: {exc}", file=sys.stderr)

    return not bool(failed)


def _write_md(path: Path, test_cases: list[TestCase]) -> None:
    lines = [f"# Test Cases\n"]
    for tc in test_cases:
        lines.append(tc.to_gherkin_scenario())
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
