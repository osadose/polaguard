import typer
import yaml
import polars as pl
import sys
from pathlib import Path
from .schema import DataContract
from .validator import ContractValidator

app = typer.Typer(add_completion=False)

@app.command()
def init(
    file: Path = typer.Option(..., help="Path to a clean sample file (csv, parquet)"),
    output: Path = typer.Option("contract.yaml", help="Where to save the generated contract")
):
    """
    Bootstrap a new data contract automatically from an existing file.
    """
    try:
        if file.suffix == ".csv":
            df = pl.read_csv(file)
        elif file.suffix == ".parquet":
            df = pl.read_parquet(file)
        else:
            typer.echo(f"Unsupported file format: {file.suffix}", err=True)
            sys.exit(1)
        
        columns_config = {}
        for col in df.columns:
            dtype = str(df[col].dtype)
            
            contract_type = "str"
            if "Int" in dtype: contract_type = "int"
            elif "Float" in dtype: contract_type = "float"
            elif "Boolean" in dtype: contract_type = "bool"
            elif "Date" in dtype: contract_type = "date"
            
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
        if file.suffix == ".csv":
            df = pl.read_csv(file)
        elif file.suffix == ".parquet":
            df = pl.read_parquet(file)
        elif file.suffix == ".json":
            df = pl.read_json(file)
        else:
            typer.echo(f"Unsupported file format: {file.suffix}", err=True)
            sys.exit(1)
    except Exception as e:
        typer.echo(f"Error loading data file: {e}", err=True)
        sys.exit(1)

    validator = ContractValidator(df, contract_obj)
    is_valid = validator.validate()
    validator.print_report()

    if not is_valid:
        sys.exit(1)

def main():
    app()

if __name__ == "__main__":
    main()