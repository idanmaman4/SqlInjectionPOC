# SQLite PDO Injection Feasibility Analyzer

This project aims to answer one security question:

> Given a SQLite/PDO SQL template and a set of constraints, is blind
> boolean-based SQL injection possible?

The current codebase provides the parsing foundation for that analysis. It
tokenizes and parses SQLite SQL with PDO-style bind placeholders:

- `?`
- `?NNN`
- `:name`
- `@name`
- `$name`

The intended final system should reason about templates, attacker-controlled
inputs, allowed characters or transformations, placeholder binding behavior,
and query semantics well enough to decide whether an attacker can construct a
boolean predicate that changes the query result without direct data output.

## Problem Model

The analyzer should take:

- A SQL template, such as a PHP/PDO query before execution.
- A set of template slots or concatenation points.
- Constraints for each slot, such as attacker-controlled vs trusted,
  parameterized vs concatenated, allowed characters, escaping, quoting context,
  length limits, type expectations, and known application predicates.
- Optional schema facts, such as table names, columns, uniqueness, nullable
  columns, and known row-existence assumptions.

It should answer:

- `not_possible`: no blind boolean-based injection path was found under the
  constraints.
- `possible`: a satisfying injection strategy exists.
- `unknown`: the analyzer lacks grammar, schema, or semantic coverage to decide
  safely.

For a `possible` result, the analyzer should explain the vulnerable slot,
quoting or expression context, constraints used, and a representative boolean
payload shape. It does not need to dump data or produce an exploit script.

## Usage

```prolog
:- use_module(sqlite_pdo_parser).

?- parse_sql("SELECT * FROM users WHERE id = ? AND email = :email", Statements).
Statements = [statement{type:select, ...}].

?- parse_sql("UPDATE users SET name = :name WHERE id = ?1", [Statement]),
   statement_placeholders(Statement, Placeholders).
Placeholders = [named(':', name), indexed(1)].
```

## API

```prolog
parse_sql(+Sql, -Statements).
parse_sql(+Sql, -Statements, +Options).
tokenize_sql(+Sql, -Tokens).
statement_placeholders(+Statement, -Placeholders).
statements_placeholders(+Statements, -Placeholders).
```

`parse_sql/3` accepts `strict(true)`. In strict mode, unknown statements fail
instead of returning a raw statement node.

## Proposed Analyzer API

The future analyzer API should sit above the parser and expose predicates like:

```prolog
injection_possible(+Template, +Constraints, -Result).
injection_possible(+Template, +Constraints, +Options, -Result).
```

Example result shape:

```prolog
Result = possible{
    kind: blind_boolean,
    slot: user_id,
    context: string_literal,
    payload_shape: "' OR <predicate> --",
    assumptions: [table_has_rows(users)],
    evidence: [...]
}.
```

The exact API can evolve, but the important contract is that the analyzer works
from a template plus constraints rather than a single already-final SQL string.

## File Layout

- `sqlite_pdo_parser.pl`: public facade and stable API.
- `sqlite_pdo_lexer.pl`: tokenizer and DCG rules for strings, identifiers,
  operators, comments, and PDO placeholders.
- `sqlite_pdo_grammar.pl`: statement splitter and grammar dispatcher.
- `grammar_rules/common.pl`: shared token-list grammar helpers.
- `grammar_rules/select.pl`: `SELECT` statement grammar.
- `grammar_rules/insert.pl`: `INSERT` statement grammar.
- `grammar_rules/update.pl`: `UPDATE` statement grammar.
- `grammar_rules/delete.pl`: `DELETE` statement grammar.
- `test_sqlite_pdo_parser.pl`: parser behavior tests.

Markdown/LaTeX grammar documentation lives in `docs/grammar/`, starting at
`docs/grammar/README.md`.

## AST Notes

Known statements use dictionaries with a `type` key:

- `select`
- `with`
- `insert`
- `update`
- `delete`
- selected schema/utility statements such as `create`, `drop`, `alter`, and
  `pragma`

Expressions are validated and stored with their original tokens, placeholders,
and a parsed expression AST:

```prolog
expr{tokens: Tokens, placeholders: Placeholders, ast: Ast}
```

The expression grammar supports literals, placeholders, identifiers, qualified
names, aliases, function calls, arithmetic/comparison/logical operators,
`LIKE`, `IN`, `BETWEEN`, `IS NULL`, parenthesized expressions, and nested
`SELECT` subqueries.

This is still a focused SQLite/PDO grammar, not a complete implementation of
every SQLite production. In `strict(true)` mode, unsupported or malformed known
statements fail instead of being accepted as raw SQL.

## Suggested Plan

1. Define the template model.

   Represent SQL templates as structured pieces instead of plain strings:

   ```prolog
   template([
       sql("SELECT * FROM users WHERE name = '"),
       slot(name),
       sql("' AND active = 1")
   ]).
   ```

   Add constraints such as:

   ```prolog
   controlled(name).
   quoted_context(name, single_quote).
   max_length(name, 64).
   allowed_chars(name, any).
   escaping(name, none).
   ```

2. Build template materialization and context analysis.

   Determine where each slot lands in the SQL grammar: string literal, numeric
   expression, identifier, operator position, comment position, or full clause
   position. This should reuse the lexer/parser but preserve slot markers.

3. Add payload-shape generation.

   Generate candidate blind boolean payload shapes based on context:

   - string literal breakout: `' OR <predicate> --`
   - numeric expression: `0 OR <predicate>`
   - parenthesized expression: `) OR <predicate> --`
   - `LIKE` pattern contexts where wildcard behavior matters

   Payload generation must respect slot constraints such as allowed characters,
   escaping, and length.

4. Add boolean predicate modeling.

   Model predicates that can flip query truth without direct output:

   - tautology vs contradiction
   - row-existence checks
   - scalar subqueries
   - `CASE WHEN` expressions
   - SQLite functions useful for boolean inference

5. Add semantic feasibility checks.

   Decide whether the injected predicate can change the observable result under
   known schema and application assumptions. For example, a tautology is only
   useful if it can broaden a filtered result set or change row existence.

6. Produce explanations.

   Return a proof-like trace: vulnerable slot, parse context, generated payload
   shape, constraints satisfied, assumptions required, and why the result is
   `possible`, `not_possible`, or `unknown`.

7. Expand tests from parser tests to security cases.

   Add positive and negative examples:

   - safe PDO placeholders
   - unsafe string concatenation
   - numeric concatenation
   - escaped quote contexts
   - restrictive allowlists
   - length-limited payloads
   - subquery-based boolean probes
   - unknown schema cases

## Tests

Run:

```sh
swipl -q -s test_sqlite_pdo_parser.pl -g run_tests,halt
```
