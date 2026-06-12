import typer
import yaml
import polars as pl
import sys
from pathlib import Path
from .schema import DataContract
from .validator import ContractValidator
from . import __version__

app = typer.Typer(add_completion=False)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"polaguard {__version__}")
        raise typer.Exit()


@app.callback()
def _main(
    version: bool = typer.Option(
        False,
        "--version",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    )
) -> None:
    _ = version


def _load_dataframe(file: Path) -> pl.DataFrame:
    suffix = file.suffix.lower()
    if suffix == ".csv":
        return pl.read_csv(file)
    if suffix == ".parquet":
        return pl.read_parquet(file)
    if suffix == ".json":
        return pl.read_json(file)
    raise ValueError(f"Unsupported file format: {file.suffix}")


def _infer_contract_type(dtype: pl.DataType) -> str:
    if dtype in {pl.Int8, pl.Int16, pl.Int32, pl.Int64, pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64}:
        return "int"
    if dtype in {pl.Float32, pl.Float64}:
        return "float"
    if dtype == pl.Boolean:
        return "bool"
    if dtype == pl.Date:
        return "date"
    if dtype.base_type() == pl.Datetime:
        return "datetime"
    return "str"

@app.command()
def init(
    file: Path = typer.Option(..., help="Path to a clean sample file (csv, parquet, json)"),
    output: Path = typer.Option("contract.yaml", help="Where to save the generated contract")
):
    """
    Bootstrap a new data contract automatically from an existing file.
    """
    try:
        df = _load_dataframe(file)
        
        columns_config = {}
        for col in df.columns:
            contract_type = _infer_contract_type(df[col].dtype)
            
            is_unique = df.select(pl.col(col).is_unique().all()).item()
            null_count = df.select(pl.col(col).is_null().sum()).item()
            has_nulls = null_count > 0

            columns_config[col] = {
                "type": contract_type,
                "required": not has_nulls,
                "unique": is_unique,
                "null_threshold": 0.0 if not has_nulls else round(null_count / df.height, 2)
            }
        
        contract_data = {
            "version": "1.0.0",
            "dataset_name": file.stem,
            "constraints": {
                "min_columns": len(df.columns),
                "min_rows": df.height,
                "allow_extra_columns": False
            },
            "columns": columns_config
        }

        with open(output, "w") as f:
            yaml.dump(contract_data, f, sort_keys=False)
            
        typer.echo(f"🎉 Successfully generated starter contract at: {output}")

    except Exception as e:
        typer.echo(f"Error initializing contract: {e}", err=True)
        sys.exit(1)

@app.command()
def check(
    file: Path = typer.Option(..., help="Path to the data file to validate"),
    contract: Path = typer.Option(..., help="Path to the YAML contract")
):
    """
    Validate a local file against a YAML data contract.
    """
    try:
        with open(contract, "r") as f:
            contract_dict = yaml.safe_load(f)
        contract_obj = DataContract(**contract_dict)
    except Exception as e:
        typer.echo(f"Error parsing contract: {e}", err=True)
        sys.exit(1)

    try:
        df = _load_dataframe(file)
    except Exception as e:
        typer.echo(f"Error loading data file: {e}", err=True)
        sys.exit(1)

    validator = ContractValidator(df, contract_obj)
    is_valid = validator.validate()
    typer.echo(validator.format_report())

    if not is_valid:
        sys.exit(1)


def main():
    app()

if __name__ == "__main__":
    main()