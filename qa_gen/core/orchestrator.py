import os
import sys

from qa_gen.config.settings import Settings
from qa_gen.core import component_resolver as comp_res
from qa_gen.core import context_assembler, form_resolver, gherkin_parser
from qa_gen.core.ai.base import AIProvider
from qa_gen.core.debug_log import log as _debug_log
from qa_gen.core.jira_client import JiraClient
from qa_gen.core.project_root import find_project_root
from qa_gen.kb.semantic_search import SemanticSearchEngine
from qa_gen.models.test_case import TestCase

# V2:
# from qa_gen.kb.embedding import EmbeddingClient
# from qa_gen.kb import supabase_client as sb

_DEFAULT_MAX_TEST_CASES = 15


def _select_provider(settings: Settings) -> AIProvider:
    provider = settings.AI_PROVIDER.lower()
    if provider == "anthropic":
        from qa_gen.core.ai.claude_client import ClaudeProvider

        return ClaudeProvider(settings.AI_API_KEY, settings.AI_MODEL_NAME)
    elif provider == "gemini":
        from qa_gen.core.ai.gemini_client import GeminiProvider

        return GeminiProvider(settings.AI_API_KEY, settings.AI_MODEL_NAME)
    else:
        print(f"Unknown AI_PROVIDER: {settings.AI_PROVIDER!r}", file=sys.stderr)
        raise SystemExit(1)


def _build_story_prompt(story_data: dict) -> str:
    fields = story_data.get("fields", {})
    summary = fields.get("summary", "")
    desc = fields.get("_parsed_description", "") or ""
    ac = fields.get("_parsed_acceptance_criteria", "") or ""
    story_id = story_data.get("key", "")

    parts = [f"JIRA Story: {story_id}", f"Summary: {summary}"]
    if desc:
        parts.append(f"Description:\n{desc}")
    if ac:
        parts.append(f"Acceptance Criteria:\n{ac}")
    parts.append("\nGenerate Gherkin test cases for this story.")
    return "\n\n".join(parts)


def _validate_output(raw_output: str, form) -> list[str]:
    from qa_gen.models.form import Form

    if not isinstance(form, Form):
        return []
    failures = []
    if "Background:" not in raw_output:
        failures.append("missing Background block")
    if "@" not in raw_output:
        failures.append("missing @tags on scenarios")
    if "Scenario Outline" not in raw_output:
        failures.append("missing Scenario Outline for multi-value tests")
    for f in form.fields:
        if f.save_on_blur and f.label.lower() not in raw_output.lower():
            failures.append(f"missing blur scenario for field '{f.id}'")
    return failures


def _blur_save_warnings(test_cases: list[TestCase], form) -> None:
    from qa_gen.models.form import Form

    if not isinstance(form, Form):
        return

    blur_behaviors = {"SAVE_ON_BLUR"}
    if form.save_behavior not in blur_behaviors:
        has_negation = any(
            "blur" in " ".join(tc.steps).lower()
            and any(
                neg in " ".join(tc.steps).lower()
                for neg in ("not save", "not persist", "does not")
            )
            for tc in test_cases
        )
        if not has_negation:
            print(
                "FR-008: no blur-does-not-save scenario detected; review AI output",
                file=sys.stderr,
            )

    for field in form.fields:
        if not field.save_on_blur:
            continue
        has_blur_save = any(
            field.label.lower() in " ".join(tc.steps).lower()
            and "blur" in " ".join(tc.steps).lower()
            for tc in test_cases
        )
        if not has_blur_save:
            print(
                f"FR-009: no blur-triggers-save scenario for field '{field.id}'",
                file=sys.stderr,
            )


def run(
    story_id: str,
    dry_run: bool,
    export_formats: list[str],
    form_override: str | None,
    no_confirm: bool,
    verbose: bool,
    settings: Settings,
    max_tests: int = _DEFAULT_MAX_TEST_CASES,
) -> list[TestCase]:
    if not sys.stdin.isatty() and not dry_run and not no_confirm:
        print(
            "interactive prompt unavailable in non-TTY — use --dry-run or --no-confirm",
            file=sys.stderr,
        )
        raise SystemExit(1)

    kb_path = settings.KB_PATH
    jira_client = JiraClient(settings.JIRA_BASE_URL, settings.JIRA_EMAIL, settings.JIRA_API_TOKEN)

    # V2: Supabase + Voyage AI clients for vector search
    # client = sb.create_supabase_client(settings)
    # embedding_client = EmbeddingClient(settings.VOYAGE_API_KEY)
    # alias_resolver = AliasResolver(client, embedding_client)

    from qa_gen.core.alias_resolver import AliasResolver

    alias_resolver = AliasResolver(kb_path)

    from qa_gen.cli.display import spinner

    if verbose:
        _debug_log(f"run start: story={story_id} dry_run={dry_run} form_override={form_override}")

    with spinner("Fetching JIRA story..."):
        story_data = jira_client.fetch_story(story_id)
        if verbose:
            summary = story_data.get("fields", {}).get("summary", "")
            _debug_log(f"fetched story: {story_id} summary={summary}")

    project_root = find_project_root()
    index_path = project_root / ".qa-gen" / "search_index.json"
    threshold = float(os.environ.get("QA_GEN_SIMILARITY_THRESHOLD", "0.75"))
    engine = SemanticSearchEngine(kb_path, index_path, threshold)
    engine.update_index()

    with spinner("Resolving form..."):
        if form_override:
            form = form_resolver.load_form(kb_path, form_override)
            if not form:
                print(
                    f"Form '{form_override}' not in KB — add YAML to {kb_path}/forms/",
                    file=sys.stderr,
                )
                raise SystemExit(3)
            form = form_resolver.flatten_inheritance(form, kb_path)
        else:
            form, _ = form_resolver.resolve_form(
                story_data, kb_path, alias_resolver, semantic_engine=engine
            )

    with spinner("Resolving components..."):
        components = comp_res.resolve_components(
            form, kb_path, alias_resolver, semantic_engine=engine
        )

    with spinner("Assembling context..."):
        context = context_assembler.assemble_context(form, components, kb_path)
        system_prompt = context_assembler.assemble_system_prompt(max_tests)

    provider = _select_provider(settings)
    story_prompt = _build_story_prompt(story_data)

    if verbose:
        _debug_log(f"provider={settings.AI_PROVIDER} model={settings.AI_MODEL_NAME}")
        _debug_log(f"story_prompt_len={len(story_prompt)} context_len={len(context)}")

    with spinner("Generating test cases..."):
        raw_output = provider.generate(system_prompt, context, story_prompt)
        if verbose:
            _debug_log(f"AI response length={len(raw_output)}")

    try:
        test_cases = gherkin_parser.parse_gherkin_to_test_cases(raw_output, story_id)
    except SystemExit:
        strict_prompt = (
            story_prompt
            + "\n\nIMPORTANT: Output ONLY valid Gherkin. Start with 'Feature:' line. "
            "Each scenario must have exactly one Given, one When, and one Then step minimum."
        )
        raw_output = provider.generate(system_prompt, context, strict_prompt)
        test_cases = gherkin_parser.parse_gherkin_to_test_cases(raw_output, story_id)

    structural_failures = _validate_output(raw_output, form)
    if structural_failures:
        missing = "; ".join(structural_failures)
        if verbose:
            _debug_log(f"structural validation failures: {missing}")
        retry_prompt = (
            story_prompt
            + f"\n\nIMPORTANT: Previous output was rejected. Fix these issues: {missing}. "
            "Output ONLY the complete corrected Gherkin Feature block."
        )
        with spinner("Retrying with structural fixes..."):
            raw_output = provider.generate(system_prompt, context, retry_prompt)
            if verbose:
                _debug_log(f"retry response length={len(raw_output)}")
        test_cases = gherkin_parser.parse_gherkin_to_test_cases(raw_output, story_id)

    if len(test_cases) > max_tests:
        print(
            f"warning: AI returned {len(test_cases)} test cases; truncating to {max_tests}",
            file=sys.stderr,
        )
        test_cases = test_cases[:max_tests]

    _blur_save_warnings(test_cases, form)
    return test_cases
