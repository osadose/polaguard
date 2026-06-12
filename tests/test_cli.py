import yaml
import polars as pl
import pytest
from typer.testing import CliRunner

from polaguard.cli import app

runner = CliRunner()


@pytest.fixture()
def tmp_csv(tmp_path):
    df = pl.DataFrame({"id": [1, 2, 3], "name": ["Alice", "Bob", "Carol"]})
    path = tmp_path / "data.csv"
    df.write_csv(path)
    return path


@pytest.fixture()
def tmp_json(tmp_path):
    df = pl.DataFrame({"id": [1, 2, 3], "name": ["Alice", "Bob", "Carol"]})
    path = tmp_path / "data.json"
    df.write_json(path)
    return path


@pytest.fixture()
def tmp_contract(tmp_path):
    contract = {
        "version": "1.0.0",
        "dataset_name": "test",
        "constraints": {"min_columns": 1, "allow_extra_columns": True},
        "columns": {
            "id": {"type": "int", "required": True, "unique": True, "null_threshold": 0.0},
            "name": {"type": "str", "required": True, "unique": False, "null_threshold": 0.0},
        },
    }
    path = tmp_path / "contract.yaml"
    with open(path, "w") as f:
        yaml.dump(contract, f)
    return path


# ---------------------------------------------------------------------------
# init command
# ---------------------------------------------------------------------------


class TestInitCommand:
    def test_init_generates_contract_from_csv(self, tmp_csv, tmp_path):
        output = tmp_path / "out.yaml"
        result = runner.invoke(app, ["init", "--file", str(tmp_csv), "--output", str(output)])
        assert result.exit_code == 0
        assert output.exists()
        with open(output) as f:
            data = yaml.safe_load(f)
        assert "columns" in data
        assert "id" in data["columns"]
        assert "name" in data["columns"]

    def test_init_inferred_types_are_correct(self, tmp_csv, tmp_path):
        output = tmp_path / "out.yaml"
        runner.invoke(app, ["init", "--file", str(tmp_csv), "--output", str(output)])
        with open(output) as f:
            data = yaml.safe_load(f)
        assert data["columns"]["id"]["type"] == "int"
        assert data["columns"]["name"]["type"] == "str"
        assert data["constraints"]["min_rows"] == 3

    def test_init_generates_contract_from_json(self, tmp_json, tmp_path):
        output = tmp_path / "out.yaml"
        result = runner.invoke(app, ["init", "--file", str(tmp_json), "--output", str(output)])
        assert result.exit_code == 0
        with open(output) as f:
            data = yaml.safe_load(f)
        assert data["columns"]["id"]["type"] == "int"

    def test_init_unsupported_format_exits_nonzero(self, tmp_path):
        bad_file = tmp_path / "data.txt"
        bad_file.write_text("hello")
        result = runner.invoke(app, ["init", "--file", str(bad_file), "--output", str(tmp_path / "c.yaml")])
        assert result.exit_code != 0

    def test_init_missing_file_exits_nonzero(self, tmp_path):
        result = runner.invoke(
            app, ["init", "--file", str(tmp_path / "missing.csv"), "--output", str(tmp_path / "c.yaml")]
        )
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# check command
# ---------------------------------------------------------------------------


class TestCheckCommand:
    def test_check_valid_file_exits_zero(self, tmp_csv, tmp_contract):
        result = runner.invoke(app, ["check", "--file", str(tmp_csv), "--contract", str(tmp_contract)])
        assert result.exit_code == 0

    def test_check_missing_contract_exits_nonzero(self, tmp_csv, tmp_path):
        result = runner.invoke(
            app, ["check", "--file", str(tmp_csv), "--contract", str(tmp_path / "nonexistent.yaml")]
        )
        assert result.exit_code != 0

    def test_check_type_violation_exits_one(self, tmp_path, tmp_contract):
        bad_df = pl.DataFrame({"id": ["a", "b", "c"], "name": ["x", "y", "z"]})
        bad_csv = tmp_path / "bad.csv"
        bad_df.write_csv(bad_csv)
        result = runner.invoke(app, ["check", "--file", str(bad_csv), "--contract", str(tmp_contract)])
        assert result.exit_code == 1

    def test_check_unsupported_format_exits_nonzero(self, tmp_path, tmp_contract):
        bad_file = tmp_path / "data.xml"
        bad_file.write_text("<root/>")
        result = runner.invoke(app, ["check", "--file", str(bad_file), "--contract", str(tmp_contract)])
        assert result.exit_code != 0

    def test_check_output_contains_dataset_name(self, tmp_csv, tmp_contract):
        result = runner.invoke(app, ["check", "--file", str(tmp_csv), "--contract", str(tmp_contract)])
        assert "test" in result.output


class TestRootOptions:
    def test_version_flag(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "polaguard" in result.output
