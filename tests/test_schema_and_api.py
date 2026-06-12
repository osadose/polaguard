import datetime

import polars as pl
import pytest
import yaml

from polaguard import load_contract, load_dataframe, validate_dataframe, validate_file
from polaguard.schema import ColumnDefinition, DataContract


def test_contract_version_must_be_semver():
    with pytest.raises(Exception):
        DataContract(version="not-semver", dataset_name="x", columns={"id": ColumnDefinition(type="int")})


def test_regex_only_allowed_for_string_columns():
    with pytest.raises(Exception):
        ColumnDefinition(type="int", regex=r"^\d+$")


def test_allowed_values_are_coerced_for_str_type():
    c = ColumnDefinition(type="str", allowed_values=[1, 2, 3])
    assert c.allowed_values == ["1", "2", "3"]


def test_allowed_values_invalid_bool_raises():
    with pytest.raises(Exception):
        ColumnDefinition(type="bool", allowed_values=["truthy"])


def test_allowed_values_date_coercion_from_iso_string():
    c = ColumnDefinition(type="date", allowed_values=["2026-01-01"])
    assert isinstance(c.allowed_values[0], datetime.date)


def test_min_rows_constraint_fails_when_below_threshold():
    df = pl.DataFrame({"id": [1]})
    contract = DataContract(
        version="1.0.0",
        dataset_name="x",
        constraints={"min_rows": 2, "min_columns": 1},
        columns={"id": ColumnDefinition(type="int")},
    )
    result = validate_dataframe(df, contract)
    assert result.is_valid is False
    assert any("rows" in err for err in result.errors)


def test_programmatic_api_load_and_validate(tmp_path):
    df = pl.DataFrame({"id": [1, 2], "name": ["a", "b"]})
    csv_path = tmp_path / "data.csv"
    contract_path = tmp_path / "contract.yaml"
    df.write_csv(csv_path)

    contract = {
        "version": "1.0.0",
        "dataset_name": "dataset",
        "constraints": {"min_columns": 2, "min_rows": 2, "allow_extra_columns": False},
        "columns": {
            "id": {"type": "int", "required": True, "unique": True, "null_threshold": 0.0},
            "name": {"type": "str", "required": True, "unique": True, "null_threshold": 0.0},
        },
    }

    with open(contract_path, "w", encoding="utf-8") as f:
        yaml.dump(contract, f)

    loaded_df = load_dataframe(csv_path)
    loaded_contract = load_contract(contract_path)
    result1 = validate_dataframe(loaded_df, loaded_contract)
    result2 = validate_file(csv_path, contract_path)

    assert result1.is_valid is True
    assert result2.is_valid is True
