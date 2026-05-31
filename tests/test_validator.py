import datetime
import polars as pl
import pytest

from polaguard.schema import ColumnDefinition, ContractConstraints, DataContract
from polaguard.validator import ContractValidator


def make_contract(**kwargs) -> DataContract:
    defaults: dict = {"version": "1.0.0", "dataset_name": "test_dataset", "columns": {}}
    defaults.update(kwargs)
    return DataContract(**defaults)


# ---------------------------------------------------------------------------
# Type checks
# ---------------------------------------------------------------------------


class TestTypeChecks:
    def test_int_column_passes(self):
        df = pl.DataFrame({"id": [1, 2, 3]})
        contract = make_contract(columns={"id": ColumnDefinition(type="int")})
        assert ContractValidator(df, contract).validate() is True

    def test_float_column_passes(self):
        df = pl.DataFrame({"price": [1.0, 2.5, 3.7]})
        contract = make_contract(columns={"price": ColumnDefinition(type="float")})
        assert ContractValidator(df, contract).validate() is True

    def test_str_column_passes(self):
        df = pl.DataFrame({"name": ["Alice", "Bob"]})
        contract = make_contract(columns={"name": ColumnDefinition(type="str")})
        assert ContractValidator(df, contract).validate() is True

    def test_bool_column_passes(self):
        df = pl.DataFrame({"active": [True, False]})
        contract = make_contract(columns={"active": ColumnDefinition(type="bool")})
        assert ContractValidator(df, contract).validate() is True

    def test_date_column_passes(self):
        df = pl.DataFrame({"created": [datetime.date(2024, 1, 1)]})
        contract = make_contract(columns={"created": ColumnDefinition(type="date")})
        assert ContractValidator(df, contract).validate() is True

    def test_datetime_column_passes(self):
        df = pl.DataFrame({"ts": [datetime.datetime(2024, 1, 1, 12, 0, 0)]})
        contract = make_contract(columns={"ts": ColumnDefinition(type="datetime")})
        assert ContractValidator(df, contract).validate() is True

    def test_type_mismatch_int_vs_str_fails(self):
        df = pl.DataFrame({"id": ["a", "b", "c"]})
        contract = make_contract(columns={"id": ColumnDefinition(type="int")})
        v = ContractValidator(df, contract)
        assert v.validate() is False
        assert any("Type Check" in e for e in v.errors)

    def test_type_mismatch_str_vs_int_fails(self):
        df = pl.DataFrame({"name": [1, 2, 3]})
        contract = make_contract(columns={"name": ColumnDefinition(type="str")})
        v = ContractValidator(df, contract)
        assert v.validate() is False
        assert any("Type Check" in e for e in v.errors)

    def test_type_mismatch_float_vs_int_fails(self):
        df = pl.DataFrame({"score": [1, 2, 3]})
        contract = make_contract(columns={"score": ColumnDefinition(type="float")})
        v = ContractValidator(df, contract)
        assert v.validate() is False
        assert any("Type Check" in e for e in v.errors)


# ---------------------------------------------------------------------------
# Missing columns
# ---------------------------------------------------------------------------


class TestMissingColumns:
    def test_required_column_missing_fails(self):
        df = pl.DataFrame({"name": ["Alice"]})
        contract = make_contract(columns={"id": ColumnDefinition(type="int", required=True)})
        v = ContractValidator(df, contract)
        assert v.validate() is False
        assert any("Missing Column" in e for e in v.errors)

    def test_optional_column_missing_passes(self):
        df = pl.DataFrame({"name": ["Alice"]})
        contract = make_contract(columns={"id": ColumnDefinition(type="int", required=False)})
        assert ContractValidator(df, contract).validate() is True


# ---------------------------------------------------------------------------
# Null threshold
# ---------------------------------------------------------------------------


class TestNullThreshold:
    def test_nulls_within_threshold_passes(self):
        df = pl.DataFrame({"score": [1.0, None, 3.0, None, 5.0]})
        contract = make_contract(columns={"score": ColumnDefinition(type="float", null_threshold=0.4)})
        assert ContractValidator(df, contract).validate() is True

    def test_nulls_exceed_threshold_fails(self):
        df = pl.DataFrame({"score": [1.0, None, None, None, 5.0]})
        contract = make_contract(columns={"score": ColumnDefinition(type="float", null_threshold=0.2)})
        v = ContractValidator(df, contract)
        assert v.validate() is False
        assert any("Null Check" in e for e in v.errors)

    def test_no_nulls_zero_threshold_passes(self):
        df = pl.DataFrame({"id": [1, 2, 3]})
        contract = make_contract(columns={"id": ColumnDefinition(type="int", null_threshold=0.0)})
        assert ContractValidator(df, contract).validate() is True


# ---------------------------------------------------------------------------
# Uniqueness
# ---------------------------------------------------------------------------


class TestUniqueness:
    def test_unique_column_passes(self):
        df = pl.DataFrame({"id": [1, 2, 3]})
        contract = make_contract(columns={"id": ColumnDefinition(type="int", unique=True)})
        assert ContractValidator(df, contract).validate() is True

    def test_duplicate_column_fails(self):
        df = pl.DataFrame({"id": [1, 1, 3]})
        contract = make_contract(columns={"id": ColumnDefinition(type="int", unique=True)})
        v = ContractValidator(df, contract)
        assert v.validate() is False
        assert any("Uniqueness Check" in e for e in v.errors)

    def test_non_unique_flag_allows_duplicates(self):
        df = pl.DataFrame({"status": ["active", "active", "inactive"]})
        contract = make_contract(columns={"status": ColumnDefinition(type="str", unique=False)})
        assert ContractValidator(df, contract).validate() is True


# ---------------------------------------------------------------------------
# Regex
# ---------------------------------------------------------------------------


class TestRegex:
    def test_regex_all_match_passes(self):
        df = pl.DataFrame({"email": ["a@b.com", "c@d.org"]})
        contract = make_contract(columns={"email": ColumnDefinition(type="str", regex=r".+@.+\..+")})
        assert ContractValidator(df, contract).validate() is True

    def test_regex_partial_mismatch_fails(self):
        df = pl.DataFrame({"email": ["not-an-email", "c@d.org"]})
        contract = make_contract(columns={"email": ColumnDefinition(type="str", regex=r".+@.+\..+")})
        v = ContractValidator(df, contract)
        assert v.validate() is False
        assert any("Regex Check" in e for e in v.errors)

    def test_regex_nulls_skipped(self):
        df = pl.DataFrame({"email": ["a@b.com", None]})
        contract = make_contract(
            columns={"email": ColumnDefinition(type="str", regex=r".+@.+\..+", null_threshold=0.5)}
        )
        assert ContractValidator(df, contract).validate() is True


# ---------------------------------------------------------------------------
# Allowed values
# ---------------------------------------------------------------------------


class TestAllowedValues:
    def test_all_allowed_passes(self):
        df = pl.DataFrame({"status": ["active", "inactive"]})
        contract = make_contract(
            columns={"status": ColumnDefinition(type="str", allowed_values=["active", "inactive", "pending"])}
        )
        assert ContractValidator(df, contract).validate() is True

    def test_disallowed_value_fails(self):
        df = pl.DataFrame({"status": ["active", "deleted"]})
        contract = make_contract(
            columns={"status": ColumnDefinition(type="str", allowed_values=["active", "inactive"])}
        )
        v = ContractValidator(df, contract)
        assert v.validate() is False
        assert any("Allowed Values" in e for e in v.errors)

    def test_nulls_excluded_from_allowed_check(self):
        df = pl.DataFrame({"status": ["active", None]})
        contract = make_contract(
            columns={"status": ColumnDefinition(type="str", null_threshold=0.5, allowed_values=["active"])}
        )
        assert ContractValidator(df, contract).validate() is True


# ---------------------------------------------------------------------------
# Structural constraints
# ---------------------------------------------------------------------------


class TestConstraints:
    def test_min_columns_passes(self):
        df = pl.DataFrame({"a": [1], "b": [2], "c": [3]})
        cols = {k: ColumnDefinition(type="int") for k in ("a", "b", "c")}
        contract = make_contract(constraints=ContractConstraints(min_columns=2), columns=cols)
        assert ContractValidator(df, contract).validate() is True

    def test_min_columns_fails(self):
        df = pl.DataFrame({"a": [1]})
        contract = make_contract(
            constraints=ContractConstraints(min_columns=3),
            columns={"a": ColumnDefinition(type="int")},
        )
        v = ContractValidator(df, contract)
        assert v.validate() is False
        assert any("Constraint Failed" in e for e in v.errors)

    def test_extra_columns_not_allowed_fails(self):
        df = pl.DataFrame({"a": [1], "b": [2], "extra": [3]})
        cols = {"a": ColumnDefinition(type="int"), "b": ColumnDefinition(type="int")}
        contract = make_contract(constraints=ContractConstraints(allow_extra_columns=False), columns=cols)
        v = ContractValidator(df, contract)
        assert v.validate() is False
        assert any("Unexpected columns" in e for e in v.errors)

    def test_extra_columns_allowed_passes(self):
        df = pl.DataFrame({"a": [1], "b": [2], "extra": [3]})
        cols = {"a": ColumnDefinition(type="int"), "b": ColumnDefinition(type="int")}
        contract = make_contract(constraints=ContractConstraints(allow_extra_columns=True), columns=cols)
        assert ContractValidator(df, contract).validate() is True


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


class TestIdempotency:
    def test_validate_twice_same_error_count(self):
        df = pl.DataFrame({"id": ["a", "b"]})
        contract = make_contract(columns={"id": ColumnDefinition(type="int")})
        v = ContractValidator(df, contract)
        v.validate()
        first_count = len(v.errors)
        v.validate()
        assert len(v.errors) == first_count

    def test_validate_twice_still_correct(self):
        df = pl.DataFrame({"id": [1, 2, 3]})
        contract = make_contract(columns={"id": ColumnDefinition(type="int")})
        v = ContractValidator(df, contract)
        assert v.validate() is True
        assert v.validate() is True


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_dataframe_existing_column_passes(self):
        df = pl.DataFrame({"id": pl.Series([], dtype=pl.Int64)})
        contract = make_contract(columns={"id": ColumnDefinition(type="int", required=True)})
        assert ContractValidator(df, contract).validate() is True

    def test_clean_data_all_checks_pass(self):
        df = pl.DataFrame(
            {
                "id": [1, 2, 3],
                "name": ["Alice", "Bob", "Carol"],
                "score": [9.5, 8.0, 7.5],
            }
        )
        contract = make_contract(
            columns={
                "id": ColumnDefinition(type="int", unique=True),
                "name": ColumnDefinition(type="str"),
                "score": ColumnDefinition(type="float"),
            }
        )
        assert ContractValidator(df, contract).validate() is True

    def test_multiple_errors_collected(self):
        df = pl.DataFrame({"id": ["a", "a"], "score": [None, None]})
        contract = make_contract(
            columns={
                "id": ColumnDefinition(type="int", unique=True),
                "score": ColumnDefinition(type="float", null_threshold=0.0),
            }
        )
        v = ContractValidator(df, contract)
        assert v.validate() is False
        assert len(v.errors) >= 2
