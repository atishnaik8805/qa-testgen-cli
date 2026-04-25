from typing import Optional

from pydantic import BaseModel


class Component(BaseModel):
    id: str
    label: str
    description: str
    interaction_steps: list[str]
    save_behavior_notes: Optional[str] = None
    forms: list[str] = []
