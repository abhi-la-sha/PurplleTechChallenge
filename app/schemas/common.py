
from pydantic import BaseModel, ConfigDict


class APISchema(BaseModel):
    """Base Pydantic model with strict configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        extra="forbid",
    )
