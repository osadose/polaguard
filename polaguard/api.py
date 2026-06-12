from dataclasses import dataclass
from pathlib import Path
from typing import List

import polars as pl
import yaml

from .schema import DataContract
from .validator import ContractValidator


@dataclass(frozen=True)
class ValidationResult:
    is_valid: bool
    errors: List[str]


def load_contract(contract_path: Path) -> DataContract:
    with open(contract_path, "r", encoding="utf-8") as f:
        contract_dict = yaml.safe_load(f)
    return DataContract(**contract_dict)


def load_dataframe(file_path: Path) -> pl.DataFrame:
    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        return pl.read_csv(file_path)
    if suffix == ".parquet":
        return pl.read_parquet(file_path)
    if suffix == ".json":
        return pl.read_json(file_path)
    raise ValueError(f"Unsupported file format: {file_path.suffix}")


def validate_dataframe(df: pl.DataFrame, contract: DataContract) -> ValidationResult:
    validator = ContractValidator(df, contract)
    is_valid = validator.validate()
    return ValidationResult(is_valid=is_valid, errors=list(validator.errors))


def validate_file(file_path: Path, contract_path: Path) -> ValidationResult:
    df = load_dataframe(file_path)
    contract = load_contract(contract_path)
    return validate_dataframe(df, contract)
