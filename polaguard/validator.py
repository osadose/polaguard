import polars as pl
from .schema import DataContract

_DTYPE_MAP: dict[str, frozenset] = {
    'int': frozenset({pl.Int8, pl.Int16, pl.Int32, pl.Int64, pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64}),
    'float': frozenset({pl.Float32, pl.Float64}),
    'str': frozenset({pl.String}),
    'bool': frozenset({pl.Boolean}),
    'date': frozenset({pl.Date}),
}


def _dtype_matches(dtype: pl.DataType, declared_type: str) -> bool:
    if declared_type == 'datetime':
        return dtype.base_type() == pl.Datetime
    return dtype in _DTYPE_MAP.get(declared_type, frozenset())


class ContractValidator:
    def __init__(self, df: pl.DataFrame, contract: DataContract):
        self.df = df
        self.contract = contract
        self.errors = []

    def validate(self) -> bool:
        self.errors.clear()
        self._check_constraints()
        self._check_columns()
        return len(self.errors) == 0

    def _check_constraints(self):
        if len(self.df.columns) < self.contract.constraints.min_columns:
            self.errors.append(
                f"Constraint Failed: Found {len(self.df.columns)} columns, "
                f"expected at least {self.contract.constraints.min_columns}."
            )

        if self.df.height < self.contract.constraints.min_rows:
            self.errors.append(
                f"Constraint Failed: Found {self.df.height} rows, "
                f"expected at least {self.contract.constraints.min_rows}."
            )

        if not self.contract.constraints.allow_extra_columns:
            contract_cols = set(self.contract.columns.keys())
            df_cols = set(self.df.columns)
            extra = df_cols - contract_cols
            if extra:
                self.errors.append(f"Constraint Failed: Unexpected columns found: {extra}")

    def _check_columns(self):
        for col_name, rules in self.contract.columns.items():
            if col_name not in self.df.columns:
                if rules.required:
                    self.errors.append(f"Missing Column: '{col_name}' is required.")
                continue

            null_count = self.df.select(pl.col(col_name).is_null().sum()).item()
            null_rate = null_count / self.df.height if self.df.height > 0 else 0

            col_dtype = self.df[col_name].dtype
            if not _dtype_matches(col_dtype, rules.type):
                self.errors.append(
                    f"Type Check: '{col_name}' has dtype {col_dtype} but contract declares '{rules.type}'."
                )

            if null_rate > rules.null_threshold:
                self.errors.append(
                    f"Null Check: '{col_name}' has {null_rate:.1%} missing values "
                    f"(allowed: {rules.null_threshold:.1%})."
                )

            if rules.unique:
                is_unique = self.df.select(pl.col(col_name).is_unique().all()).item()
                if not is_unique:
                    dups = self.df.height - self.df.select(pl.col(col_name).n_unique()).item()
                    self.errors.append(f"Uniqueness Check: '{col_name}' contains {dups} duplicate values.")

            if rules.regex and rules.type == 'str':
                invalid_regex_count = self.df.filter(
                    pl.col(col_name).is_not_null()
                ).select(
                    pl.col(col_name).cast(pl.String).str.contains(rules.regex).not_().sum()
                ).item()
                
                if invalid_regex_count > 0:
                    self.errors.append(
                        f"Regex Check: '{col_name}' had {invalid_regex_count} values "
                        f"failing pattern '{rules.regex}'."
                    )

            if rules.allowed_values:
                invalid_count = self.df.filter(
                    pl.col(col_name).is_not_null()
                ).select(
                    (~pl.col(col_name).is_in(rules.allowed_values)).sum()
                ).item()
                
                if invalid_count > 0:
                    self.errors.append(
                        f"Allowed Values: '{col_name}' had {invalid_count} values "
                        f"not in allowed list {rules.allowed_values}."
                    )

    def format_report(self) -> str:
        if not self.errors:
            return f"✅ Contract '{self.contract.dataset_name}' Passed!"

        lines = [
            f"❌ Contract '{self.contract.dataset_name}' Failed with {len(self.errors)} errors:"
        ]
        lines.extend(f" - {err}" for err in self.errors)
        return "\n".join(lines)

    def print_report(self):
        # Kept for backward compatibility. Prefer format_report() for programmatic usage.
        report = self.format_report()
        import sys

        sys.stdout.write(report + "\n")