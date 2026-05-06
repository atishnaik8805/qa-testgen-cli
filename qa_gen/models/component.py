from typing import Optional

from pydantic import BaseModel


class Component(BaseModel):
    id: str
    label: str
    description: str
    interaction_steps: list[str]
    save_behavior_notes: Optional[str] = None
    required_test_patterns: list[str] = []
    forms: list[str] = []
