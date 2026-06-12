from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


def _coerce_allowed_value(value: Any, declared_type: str) -> Any:
    if declared_type == "int":
        return int(value)
    if declared_type == "float":
        return float(value)
    if declared_type == "str":
        return str(value)
    if declared_type == "bool":
        if isinstance(value, bool):
            return value
        lowered = str(value).strip().lower()
        if lowered in {"true", "1", "yes", "y"}:
            return True
        if lowered in {"false", "0", "no", "n"}:
            return False
        raise ValueError(f"Cannot coerce {value!r} to bool")
    if declared_type == "date":
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        return date.fromisoformat(str(value))
    if declared_type == "datetime":
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value))
    return value

class ColumnDefinition(BaseModel):
    type: Literal['int', 'float', 'str', 'bool', 'date', 'datetime']
    required: bool = True
    unique: bool = False
    null_threshold: float = Field(default=0.0, ge=0.0, le=1.0)
    regex: Optional[str] = None
    allowed_values: Optional[List[Any]] = None

    @model_validator(mode="after")
    def _validate_definition(self) -> "ColumnDefinition":
        if self.regex is not None and self.type != "str":
            raise ValueError("regex is only supported for columns with type='str'")

        if self.allowed_values is not None:
            coerced: List[Any] = []
            for value in self.allowed_values:
                coerced.append(_coerce_allowed_value(value, self.type))
            self.allowed_values = coerced

        return self

class ContractConstraints(BaseModel):
    min_columns: int = 0
    min_rows: int = 0
    allow_extra_columns: bool = True

class DataContract(BaseModel):
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    dataset_name: str
    constraints: ContractConstraints = Field(default_factory=ContractConstraints)
    columns: Dict[str, ColumnDefinition]