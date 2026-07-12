"""Bounded Boolean SQL-injection analysis for SQLite query templates."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
import sqlite3
from typing import Any, Iterable


TEMPLATE_HOLE = "?"
NOT_FOUND_RESPONSE = "user not found"
FOUND_RESPONSE = "user found"
VALID_CONTEXTS = {"numeric", "string_value", "string_single"}


@dataclass(frozen=True)
class PdoQuery:
    """Compatibility name for an unsafe SQL template.

    ``?`` marks the location where attacker-controlled text is interpolated
    before SQLite parses the statement. The analyzer separately models a real
    PDO bind through the ``pdo_bound`` constraint.
    """

    sql: str


def pdo_query(sql: str) -> PdoQuery:
    return PdoQuery(sql)


Constraint = tuple[Any, ...]


def legal_injections(
    query: PdoQuery | str,
    constraints: list[Constraint],
    *,
    limit: int = 20,
    max_padding: int = 4,
) -> list[dict[str, Any]]:
    """Return confirmed true/false Boolean-oracle witnesses.

    The search is intentionally bounded. An empty result means that no witness
    was found in this model, not that the target is proven safe.
    """

    validate_search_options(limit=limit, max_padding=max_padding)
    validate_constraints(constraints)
    if limit == 0 or not is_controlled(constraints) or is_bound_safely(constraints):
        return []

    sql = normalize_query(query)
    before, after = split_single_placeholder(sql)
    ensure_read_only_select(sql)
    context = context_for(before, after, constraints)

    witnesses: list[dict[str, Any]] = []
    connection = representative_connection()
    try:
        for pair in boolean_payload_pairs(context, max_padding=max_padding):
            true_payload, false_payload = pair
            if not satisfies_constraints(true_payload, constraints):
                continue
            if not satisfies_constraints(false_payload, constraints):
                continue

            true_sql = before + true_payload + after
            false_sql = before + false_payload + after
            true_outcome = execute_as_website(connection, true_sql)
            false_outcome = execute_as_website(connection, false_sql)
            if not true_outcome["ok"] or not false_outcome["ok"]:
                continue
            if true_outcome["response"] == false_outcome["response"]:
                continue
            if true_outcome["response"] == NOT_FOUND_RESPONSE:
                continue
            if false_outcome["response"] != NOT_FOUND_RESPONSE:
                continue

            witnesses.append(
                {
                    "kind": "confirmed_boolean_oracle",
                    "parameter": "param",
                    "context": context,
                    "true_payload": true_payload,
                    "false_payload": false_payload,
                    "true_final_sql": true_sql,
                    "false_final_sql": false_sql,
                    "true_response": true_outcome["response"],
                    "false_response": false_outcome["response"],
                    "nested_query_template": nested_query_template(context),
                    "nested_query_example": nested_query_example(context),
                    "evidence": [
                        "single_explicit_template_hole",
                        "representative_users_table_seeded",
                        "both_statements_executed_without_error",
                        "true_probe_returned_a_row",
                        "false_probe_returned_no_rows",
                    ],
                }
            )
            if len(witnesses) >= limit:
                break
    finally:
        connection.close()
    return witnesses


def injection_possible(query: PdoQuery | str, constraints: list[Constraint]) -> bool:
    return bool(legal_injections(query, constraints, limit=1))


def analyze(
    query: PdoQuery | str,
    constraints: list[Constraint],
    *,
    limit: int = 20,
    max_padding: int = 4,
) -> dict[str, Any]:
    validate_search_options(limit=limit, max_padding=max_padding)
    validate_constraints(constraints)
    sql = normalize_query(query)
    before, after = split_single_placeholder(sql)
    ensure_read_only_select(sql)

    if is_bound_safely(constraints):
        return {
            "status": "safe_by_parameterization",
            "injections": [],
            "message": "Bound values are data literals and cannot alter the SQL structure.",
        }
    if not is_controlled(constraints):
        return {
            "status": "not_attacker_controlled",
            "injections": [],
            "message": "The modeled value is not attacker controlled.",
        }

    context = context_for(before, after, constraints)
    schema_error = representative_schema_error(before, after, context)
    if schema_error is not None:
        return {
            "status": "unsupported_query_schema",
            "injections": [],
            "message": f"The representative PoC database cannot execute this query: {schema_error}",
        }

    injections = legal_injections(
        query,
        constraints,
        limit=limit,
        max_padding=max_padding,
    )
    if injections:
        return {
            "status": "confirmed_boolean_oracle",
            "injections": injections,
            "message": "A true/false response distinction was reproduced against the PoC database.",
        }
    return {
        "status": "no_witness_within_bounds",
        "injections": [],
        "message": "No Boolean witness was found in the configured search bounds; this is not proof of safety.",
    }


def normalize_query(query: PdoQuery | str) -> str:
    if isinstance(query, PdoQuery):
        return query.sql
    return str(query)


def split_single_placeholder(sql: str) -> tuple[str, str]:
    if sql.count(TEMPLATE_HOLE) != 1:
        raise ValueError(f"SQL template must contain exactly one {TEMPLATE_HOLE} hole")
    return tuple(sql.split(TEMPLATE_HOLE, 1))  # type: ignore[return-value]


def ensure_read_only_select(sql: str) -> None:
    if not sql.lstrip().upper().startswith("SELECT"):
        raise ValueError("The PoC executes read-only SELECT templates only")


def representative_schema_error(before: str, after: str, context: str) -> str | None:
    """Return the SQLite error for a neutral substitution, if any.

    This keeps a query that references an unknown table or column from being
    reported as merely having no Boolean witness.
    """

    neutral = "" if context == "string_single" else "''" if context == "string_value" else "0"
    connection = representative_connection()
    try:
        outcome = execute_as_website(connection, before + neutral + after)
        return None if outcome["ok"] else str(outcome["error"])
    finally:
        connection.close()


def context_for(before: str, after: str, constraints: list[Constraint]) -> str:
    explicit = find_constraint(constraints, "context")
    if explicit is not None:
        context = str(explicit[2])
        if context not in VALID_CONTEXTS:
            raise ValueError(f"Unsupported context: {context}")
        return context
    if before.endswith("'") and after.startswith("'"):
        return "string_single"
    return "numeric"


def boolean_payload_pairs(context: str, *, max_padding: int) -> Iterable[tuple[str, str]]:
    if context == "string_single":
        prefix = "'"
    elif context == "string_value":
        prefix = "''"
    elif context == "numeric":
        prefix = "0"
    else:  # Defensive: context_for() validates public input.
        raise ValueError(f"Unsupported context: {context}")

    true_tokens = (prefix, "OR", "1", "=", "1", "--")
    false_tokens = (prefix, "AND", "1", "=", "0", "--")
    true_variants = render_token_variants(true_tokens, max_padding=max_padding)
    false_variants = render_token_variants(false_tokens, max_padding=max_padding)
    pairs = product(true_variants, false_variants)
    yield from sorted(pairs, key=lambda item: (max(map(len, item)), sum(map(len, item)), item))


def nested_query_template(context: str) -> str:
    """Show where a data-dependent scalar subquery belongs in the payload."""

    prefix = "'" if context == "string_single" else "''" if context == "string_value" else "0"
    return f"{prefix} OR (SELECT CASE WHEN (<nested query predicate>) THEN 1 ELSE 0 END)=1--"


def nested_query_example(context: str) -> str:
    """Return a harmless example using only the representative PoC schema."""

    prefix = "'" if context == "string_single" else "''" if context == "string_value" else "0"
    predicate = "(SELECT active FROM users WHERE username='alice' LIMIT 1)=1"
    return f"{prefix} OR (SELECT CASE WHEN ({predicate}) THEN 1 ELSE 0 END)=1--"


def render_token_variants(tokens: tuple[str, ...], *, max_padding: int) -> list[str]:
    variants = {
        "".join(
            token + (separators[index] if index < len(separators) else "")
            for index, token in enumerate(tokens)
        )
        for separators in product(("", " "), repeat=len(tokens) - 1)
        if separators.count(" ") <= max_padding
    }
    return sorted(variants, key=lambda value: (len(value), value))


def representative_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.execute(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, name TEXT, active INTEGER, c INTEGER)"
    )
    connection.executemany(
        "INSERT INTO users (id, username, name, active, c) VALUES (?, ?, ?, ?, ?)",
        [
            (1, "alice", "Alice", 1, 1),
            (2, "bob", "Bob", 0, 2),
        ],
    )
    connection.execute(
        "CREATE TABLE accounts (id INTEGER PRIMARY KEY, unusual_column TEXT, c INTEGER)"
    )
    connection.execute("INSERT INTO accounts VALUES (1, 'seed', 1)")
    return connection


def execute_as_website(connection: sqlite3.Connection, sql: str) -> dict[str, Any]:
    try:
        row = connection.execute(sql).fetchone()
    except sqlite3.Error as exc:
        return {"ok": False, "response": None, "error": str(exc)}
    return {
        "ok": True,
        "response": FOUND_RESPONSE if row is not None else NOT_FOUND_RESPONSE,
        "error": None,
    }


def is_controlled(constraints: list[Constraint]) -> bool:
    return ("controlled", "param") in constraints


def is_bound_safely(constraints: list[Constraint]) -> bool:
    return any(
        constraint in constraints
        for constraint in [
            ("pdo_bound", "param"),
            ("parameterized", "param"),
            ("escaping", "param", "pdo_parameter"),
        ]
    )


def satisfies_constraints(payload: str, constraints: list[Constraint]) -> bool:
    max_length = find_constraint(constraints, "max_length")
    if max_length is not None and len(payload) > int(max_length[2]):
        return False

    allowed = find_constraint(constraints, "allowed_chars")
    if allowed is not None and allowed[2] != "any":
        allowed_chars = set(str(allowed[2]))
        if any(char not in allowed_chars for char in payload):
            return False

    required = [
        item[2]
        for item in constraints
        if len(item) == 3 and item[:2] == ("require_char", "param")
    ]
    return all(str(char) in payload for char in required)


def find_constraint(constraints: list[Constraint], name: str) -> Constraint | None:
    for constraint in constraints:
        if constraint and constraint[0] == name and len(constraint) >= 2 and constraint[1] == "param":
            return constraint
    return None


def validate_search_options(*, limit: int, max_padding: int) -> None:
    if not isinstance(limit, int) or not 0 <= limit <= 100:
        raise ValueError("Result limit must be between 0 and 100")
    if not isinstance(max_padding, int) or not 0 <= max_padding <= 5:
        raise ValueError("Max padding must be between 0 and 5")


def validate_constraints(constraints: list[Constraint]) -> None:
    value_constraints = {"context", "max_length", "allowed_chars", "require_char", "escaping"}
    flag_constraints = {"controlled", "pdo_bound", "parameterized"}
    for constraint in constraints:
        if not isinstance(constraint, tuple) or len(constraint) < 2 or constraint[1] != "param":
            raise ValueError(f"Invalid constraint: {constraint!r}")
        name = constraint[0]
        expected_length = 3 if name in value_constraints else 2 if name in flag_constraints else None
        if expected_length is None or len(constraint) != expected_length:
            raise ValueError(f"Invalid constraint: {constraint!r}")
        if name == "max_length" and int(constraint[2]) < 0:
            raise ValueError("Maximum payload length cannot be negative")
    explicit_context = find_constraint(constraints, "context")
    if explicit_context is not None and explicit_context[2] not in VALID_CONTEXTS:
        raise ValueError(f"Unsupported context: {explicit_context[2]}")


def constraint_from_form(
    *,
    controlled: bool,
    context: str,
    max_length: str,
    allowed_chars: str,
    pdo_bound: bool,
) -> list[Constraint]:
    constraints: list[Constraint] = []
    if controlled:
        constraints.append(("controlled", "param"))
    if pdo_bound:
        constraints.append(("pdo_bound", "param"))
    if context:
        constraints.append(("context", "param", context))
    if max_length.strip():
        parsed_length = int(max_length)
        if parsed_length < 0:
            raise ValueError("Maximum payload length cannot be negative")
        constraints.append(("max_length", "param", parsed_length))
    constraints.append(
        ("allowed_chars", "param", allowed_chars if allowed_chars.strip() else "any")
    )
    validate_constraints(constraints)
    return constraints
