from typing import Optional

from pydantic import BaseModel, field_validator


class Field(BaseModel):
    id: str
    label: str
    type: str
    required: bool
    save_on_blur: bool = False
    component: Optional[str] = None
    save_behavior: Optional[str] = None
    save_trigger: Optional[str] = None


class Form(BaseModel):
    form_id: str
    display_name: Optional[str] = None
    module: Optional[str] = None
    save_behavior: str
    save_trigger: str
    validation_timing: Optional[str] = None
    fields: list[Field]
    extends: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("form_id")
    @classmethod
    def form_id_snake_case(cls, v: str) -> str:
        if v != v.lower().replace("-", "_"):
            raise ValueError(f"form_id must be snake_case, got: {v!r}")
        return v
