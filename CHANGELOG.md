# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project follows Semantic Versioning.

## [0.1.0] - 2026-06-12
### Added
- Initial release of polaguard CLI.
- Contract validation for CSV, Parquet, and JSON inputs.
- Contract schema validation with Pydantic models.
- Programmatic API: `load_contract`, `load_dataframe`, `validate_dataframe`, and `validate_file`.
- Comprehensive unit and CLI test coverage.
- Global `--version` CLI flag.
- `py.typed` marker for typed package consumers.

### Changed
- Improved dtype inference for contract generation using Polars datatype classes.
- Added `min_rows` constraint support in contract constraints and validation.
- Hardened contract version format to semantic version format (`X.Y.Z`).
- Added schema-level validation for invalid `regex` usage on non-string columns.
- Added coercion for `allowed_values` to align with declared column type.

### Fixed
- Validation report rendering no longer depends on direct `print` calls from CLI path.
- Validator now supports safe programmatic report formatting via `format_report()`.
- Removed unnecessary hard dependency on `pyarrow`.
