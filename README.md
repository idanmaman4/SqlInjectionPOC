# SQLite PDO Injection Feasibility Analyzer

This project asks:

> Given a SQLite PDO statement containing one `?` parameter and a set of
> constraints, is blind boolean-based SQL injection possible?

The current implementation is Python-only. It performs a bounded search for
paired true/false Boolean probes and provides a Flask frontend for interactive
use.

## Scope

The analyzer currently supports:

- One SQLite/PDO statement containing exactly one positional `?`.
- Constraints for that one parameter, named `param`.
- Blind boolean payload generation for quoted string, unquoted string-value,
  and numeric contexts.
- Lazy generation: ask for more results by increasing the result limit.

The analyzer returns representative legal payloads; it does not dump data or
produce exploit scripts.

## Python Usage

```python
from pdo_kanren import legal_injections, pdo_query

query = pdo_query("SELECT * FROM users WHERE name = '?' AND active = 1")
constraints = [("controlled", "param"), ("allowed_chars", "param", "any")]

for item in legal_injections(query, constraints, limit=3):
    print(item["true_payload"], item["false_payload"])
    print(item["true_final_sql"], item["false_final_sql"])
```

Use `max_length` to constrain the parameter:

```python
constraints = [
    ("controlled", "param"),
    ("max_length", "param", 20),
]
```

Common constraints:

- `("controlled", "param")`
- `("pdo_bound", "param")`
- `("context", "param", "numeric")`
- `("context", "param", "string_value")`
- `("max_length", "param", 20)`
- `("allowed_chars", "param", "any")`

## Run The Server With uv

From the repo root:

```sh
uv run sqlite-pdo-analyzer
```

Then open:

```text
http://127.0.0.1:5000
```

You can override the host or port:

```sh
SQLITE_PDO_ANALYZER_PORT=5050 uv run sqlite-pdo-analyzer
```

## Install As A uv Tool

From the repo root:

```sh
uv tool install .
sqlite-pdo-analyzer
```

To update the installed tool after local edits:

```sh
uv tool install . --force
```

## File Layout

- `pdo_kanren/mini.py`: retained tiny relational-core utility.
- `pdo_kanren/analyzer.py`: one-parameter PDO injection analyzer.
- `pdo_kanren/web.py`: Flask frontend and console entry point.
- `pdo_kanren/templates/index.html`: frontend form and results page.
- `pdo_kanren/static/styles.css`: frontend styling.
- `pyproject.toml`: uv/package metadata and `sqlite-pdo-analyzer` script.
- `app.py`: compatibility shim for Flask imports.
- `tests/`: pytest/unittest-compatible test suite.

## Tests

```sh
uv run pytest
```
