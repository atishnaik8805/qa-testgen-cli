from typing import Literal

from pydantic import BaseModel


class TestCase(BaseModel):
    title: str
    type: Literal["positive", "negative", "edge"]
    preconditions: list[str]
    steps: list[str]
    expected_result: str
    story_id: str

    def to_gherkin_scenario(self) -> str:
        lines = [f"  Scenario: {self.title}"]
        for pre in self.preconditions:
            lines.append(f"    Given {pre}")
        for i, step in enumerate(self.steps):
            keyword = "When" if i == 0 else "And"
            lines.append(f"    {keyword} {step}")
        lines.append(f"    Then {self.expected_result}")
        return "\n".join(lines)

    def to_zephyr_step(self) -> dict:
        return {
            "description": " → ".join(self.steps),
            "testData": "",
            "expectedResult": self.expected_result,
        }
