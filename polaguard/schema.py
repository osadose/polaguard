from typing import List, Optional, Literal, Any, Dict
from pydantic import BaseModel, Field

class ColumnDefinition(BaseModel):
    type: Literal['int', 'float', 'str', 'bool', 'date', 'datetime']
    required: bool = True
    unique: bool = False
    null_threshold: float = Field(default=0.0, ge=0.0, le=1.0)
    regex: Optional[str] = None
    allowed_values: Optional[List[Any]] = None

class ContractConstraints(BaseModel):
    min_columns: int = 0
    allow_extra_columns: bool = True

class DataContract(BaseModel):
    version: str
    dataset_name: str
    constraints: ContractConstraints = Field(default_factory=ContractConstraints)
    columns: Dict[str, ColumnDefinition]