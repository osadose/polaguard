# polaguard

**Lightning-fast local data contract validation for CSV and Parquet files.**  
Built to protect local pipelines, software loops, and CI/CD runners before data hits the cloud.

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](https://github.com/osadose/polaguard/blob/main/LICENSE)
[![Powered by Polars](https://img.shields.io/badge/powered%20by-Polars-orange.svg)](https://pola.rs)

## ⚡ Why Polaguard?
Most data contract engines are database-centric, slow to connect, and heavy. **Polaguard** shifts data quality left:
*   **Zero Infrastructure:** No cloud dependencies, database logins, or heavy configuration.
*   **Blazing Fast:** Vectorized execution handling millions of rows in milliseconds using [Polars](https://pola.rs).
*   **Pipeline Native:** Designed to block git commits and GitHub Action pipelines via automated exit codes.

## 🚀 Quick Start

### 1. Install
```bash
pip install polaguard
```

### 2. Auto-Generate a Contract Schema
Point Polaguard at a clean file. It will automatically infer your structures, formats, uniqueness, and null distributions.
```bash
polaguard init --file data/baseline.parquet --output contract.yaml
```

### 3. Check Incoming Batches
Instantly check incoming files against your established standards:
```bash
polaguard check --file data/new_batch.csv --contract contract.yaml
```

## 🛠️ Automated Integrations

### Pre-Commit Hooks
Catch structure breaking data changes before making a git commit. Add this to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/osadose/polaguard
    rev: v0.1.0
    hooks:
      - id: polaguard
        args: ["check", "--file", "data/raw_inputs.csv", "--contract", "contract.yaml"]
```