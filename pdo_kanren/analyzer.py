"""Relational analyzer for one-parameter SQLite PDO statements."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
import sqlite3
from typing import Any, Iterable

from .mini import Goal, eq, run, var


@dataclass(frozen=True)
class PdoQuery:
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
    q = var("result")
    return run(limit, q, legal_injectiono(query, constraints, q, max_padding=max_padding))


def injection_possible(query: PdoQuery | str, constraints: list[Constraint]) -> bool:
    return bool(legal_injections(query, constraints, limit=1))


def analyze(
    query: PdoQuery | str,
    constraints: list[Constraint],
    *,
    limit: int = 20,
    max_padding: int = 4,
) -> dict[str, Any]:
    injections = legal_injections(query, constraints, limit=limit, max_padding=max_padding)
    if not injections:
        return {"status": "not_possible", "injections": []}
    return {"status": "possible", "injections": injections}


def legal_injectiono(
    query: PdoQuery | str,
    constraints: list[Constraint],
    result: Any,
    *,
    max_padding: int = 4,
) -> Goal:
    sql = normalize_query(query)
    before, after = split_single_placeholder(sql)
    context = context_for(before, after, constraints)

    def goal(state: dict[Any, Any]) -> Iterable[dict[Any, Any]]:
        if not is_controlled(constraints) or is_bound_safely(constraints):
            return
        for payload in payloads_for_context(
            context,
            before=before,
            after=after,
            constraints=constraints,
            max_depth=max_padding,
        ):
            final_sql = before + payload["text"] + after
            candidate = {
                "kind": "valid_sql_substitution",
                "parameter": "param",
                "context": context,
                "payload": payload["text"],
                "payload_shape": payload["shape"],
                "final_sql": final_sql,
                "evidence": ["single_pdo_placeholder", *payload["evidence"]],
            }
            yield from eq(result, candidate)(state)

    return goal


def normalize_query(query: PdoQuery | str) -> str:
    if isinstance(query, PdoQuery):
        return query.sql
    return str(query)


def split_single_placeholder(sql: str) -> tuple[str, str]:
    if sql.count("?") != 1:
        raise ValueError("PDO query must contain exactly one positional ? placeholder")
    before, after = sql.split("?", 1)
    return before, after


def context_for(before: str, after: str, constraints: list[Constraint]) -> str:
    explicit = find_constraint(constraints, "context")
    if explicit is not None:
        return str(explicit[2])
    if before.endswith("'") and after.startswith("'"):
        return "string_single"
    return "numeric"


SQL_QUOTE_ATOMS = ("'", "''")
SQL_OPERATOR_ATOMS = ("--", "OR", "AND", "=", "<>", "(", ")")
SQL_LITERAL_ATOMS = ("1", "0", "NULL")
SQL_KEYWORD_ATOMS = ("EXISTS", "SELECT")
SQL_IDENTIFIER_ATOMS = ("c",)
SQL_ATOMS = (
    *SQL_QUOTE_ATOMS,
    *SQL_OPERATOR_ATOMS,
    *SQL_LITERAL_ATOMS,
    *SQL_KEYWORD_ATOMS,
    *SQL_IDENTIFIER_ATOMS,
)

STRUCTURAL_ATOMS = {"'", "''", "--", "OR", "AND", "=", "<>", "EXISTS", "SELECT"}
VALID_SQLITE_SCHEMA_ERRORS = (
    "no such table",
    "no such column",
    "no such function",
    "ambiguous column",
)


def payloads_for_context(
    context: str,
    *,
    before: str,
    after: str,
    constraints: list[Constraint],
    max_depth: int,
) -> Iterable[dict[str, Any]]:
    for atoms in candidate_atom_sequences(
        context,
        constraints=constraints,
        max_depth=max_depth,
    ):
        if not looks_like_injection(atoms, context):
            continue
        text = payload_text(atoms)
        if not satisfies_constraints(text, constraints):
            continue
        final_sql = before + text + after
        if not sqlite_accepts_statement(final_sql):
            continue
        yield {
            "text": text,
            "shape": "sqlite_valid_token_sequence",
            "evidence": [
                "generated_from_sql_atoms",
                "minimal_fixed_token_vocabulary",
                "shortest_first_bounded_search",
                "sqlite_accepts_substituted_statement",
                *evidence_for_atoms(atoms),
            ],
        }


def candidate_atom_sequences(
    context: str,
    *,
    constraints: list[Constraint],
    max_depth: int,
) -> Iterable[tuple[str, ...]]:
    vocabulary = allowed_atoms(SQL_ATOMS, constraints)
    for token_count in range(1, max(1, max_depth) + 1):
        if not can_fit_token_count(token_count, vocabulary, constraints):
            continue
        for atoms in product(vocabulary, repeat=token_count):
            if "--" in atoms[:-1]:
                continue
            yield atoms


def allowed_atoms(atoms: tuple[str, ...], constraints: list[Constraint]) -> tuple[str, ...]:
    return tuple(atom for atom in atoms if atom_allowed(atom, constraints))


def atom_allowed(atom: str, constraints: list[Constraint]) -> bool:
    allowed = find_constraint(constraints, "allowed_chars")
    if allowed is None or allowed[2] == "any":
        return True
    allowed_chars = set(str(allowed[2]))
    return all(char in allowed_chars for char in atom)


def can_fit_token_count(
    token_count: int,
    vocabulary: tuple[str, ...],
    constraints: list[Constraint],
) -> bool:
    if not vocabulary:
        return False
    max_length = find_constraint(constraints, "max_length")
    if max_length is None:
        return True
    length_limit = max(0, int(max_length[2]))
    shortest_atom = min(len(atom) for atom in vocabulary)
    shortest_payload = (shortest_atom * token_count) + (token_count - 1)
    return shortest_payload <= length_limit


def payload_text(atoms: tuple[str, ...]) -> str:
    return " ".join(atoms)


def looks_like_injection(atoms: tuple[str, ...], context: str) -> bool:
    if context == "string_single" and atoms[:1] != ("'",):
        return False
    if context == "string_value" and atoms[:1] != ("''",):
        return False
    if context == "numeric" and atoms[:1] not in {("1",), ("0",), ("NULL",), ("c",)}:
        return False
    if context in {"numeric", "string_value"} and len(atoms) == 1:
        return False
    return any(atom in STRUCTURAL_ATOMS for atom in atoms[1:])


def sqlite_accepts_statement(sql: str) -> bool:
    connection = sqlite3.connect(":memory:")
    try:
        connection.execute(f"EXPLAIN {sql}")
    except sqlite3.Error as exc:
        message = str(exc).lower()
        return message.startswith(VALID_SQLITE_SCHEMA_ERRORS)
    finally:
        connection.close()
    return True


def evidence_for_atoms(atoms: tuple[str, ...]) -> list[str]:
    evidence = []
    if atoms[:1] == ("'",):
        evidence.append("uses_quote_atom")
    if "--" in atoms:
        evidence.append("uses_comment_atom")
    if any(atom in {"OR", "AND"} for atom in atoms):
        evidence.append("uses_boolean_operator_atom")
    return evidence


def is_controlled(constraints: list[Constraint]) -> bool:
    return ("controlled", "param") in constraints


def is_bound_safely(constraints: list[Constraint]) -> bool:
    return any(
        constraint in constraints
        for constraint in [
            ("pdo_bound", "param"),
            ("parameterized", "param"),
            ("escaping", "param", "pdo_parameter"),
            ("escaping", "param", "sql_quote"),
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

    required = [item[2] for item in constraints if len(item) == 3 and item[:2] == ("require_char", "param")]
    return all(str(char) in payload for char in required)


def find_constraint(constraints: list[Constraint], name: str) -> Constraint | None:
    for constraint in constraints:
        if constraint and constraint[0] == name and len(constraint) >= 2 and constraint[1] == "param":
            return constraint
    return None


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
        constraints.append(("max_length", "param", int(max_length)))
    if allowed_chars.strip():
        constraints.append(("allowed_chars", "param", allowed_chars))
    else:
        constraints.append(("allowed_chars", "param", "any"))
    return constraints
