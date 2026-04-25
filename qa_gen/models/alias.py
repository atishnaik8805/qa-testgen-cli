from typing import Literal

from pydantic import BaseModel


class Alias(BaseModel):
    phrase: str
    target_id: str
    target_type: Literal["form", "component"]
