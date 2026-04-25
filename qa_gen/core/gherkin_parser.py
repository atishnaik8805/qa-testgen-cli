import re
import sys

from gherkin.errors import ParserError
from gherkin.parser import Parser
from gherkin.token_scanner import TokenScanner

from qa_gen.models.test_case import TestCase


def validate_gherkin(text: str) -> list[str]:
    try:
        parser = Parser()
        parser.parse(TokenScanner(text))
        return []
    except ParserError as e:
        return [str(e)]


def parse_gherkin_to_test_cases(text: str, story_id: str) -> list[TestCase]:
    errors = validate_gherkin(text)
    if errors:
        print(f"AI output failed Gherkin parse: {errors}", file=sys.stderr)
        raise SystemExit(4)

    test_cases: list[TestCase] = []
    # Extract Feature title for context
    feature_match = re.search(r"^Feature:\s*(.+)$", text, re.MULTILINE)

    scenario_pattern = re.compile(
        r"Scenario:\s*(.+?)\n((?:[ \t]+(?:Given|When|Then|And|But).+\n?)+)",
        re.MULTILINE,
    )

    for match in scenario_pattern.finditer(text):
        title = match.group(1).strip()
        body = match.group(2)

        preconditions: list[str] = []
        steps: list[str] = []
        expected_result = ""

        lines = [l.strip() for l in body.strip().splitlines() if l.strip()]
        in_given = True
        for line in lines:
            for kw in ("Given ", "When ", "Then ", "And ", "But "):
                if line.startswith(kw):
                    content = line[len(kw):].strip()
                    if line.startswith("Given "):
                        preconditions.append(content)
                        in_given = True
                    elif line.startswith("Then "):
                        expected_result = content
                        in_given = False
                    elif line.startswith(("When ", "And ", "But ")):
                        if in_given and preconditions and not steps:
                            # Still in given block
                            if line.startswith("And ") or line.startswith("But "):
                                preconditions.append(content)
                            else:
                                steps.append(content)
                                in_given = False
                        else:
                            steps.append(content)
                            in_given = False
                    break

        if not expected_result and steps:
            expected_result = steps.pop()

        tc_type: str = "positive"
        title_lower = title.lower()
        if any(w in title_lower for w in ("invalid", "missing", "empty", "fail", "error", "reject")):
            tc_type = "negative"
        elif any(w in title_lower for w in ("edge", "boundary", "max", "min", "limit")):
            tc_type = "edge"

        if title and (steps or preconditions):
            test_cases.append(
                TestCase(
                    title=title,
                    type=tc_type,  # type: ignore[arg-type]
                    preconditions=preconditions,
                    steps=steps,
                    expected_result=expected_result,
                    story_id=story_id,
                )
            )

    return test_cases
