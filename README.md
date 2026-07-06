# SQLite PDO Parser for SWI-Prolog

Small SWI-Prolog parser for SQLite SQL that understands PDO-style bind
placeholders:

- `?`
- `?NNN`
- `:name`
- `@name`
- `$name`

The parser is intended for static analysis and SQL-injection experiments. It
parses common SQLite statements into dictionaries and preserves unsupported SQL
as token lists instead of silently dropping it.

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

## Tests

Run:

```sh
swipl -q -s test_sqlite_pdo_parser.pl -g run_tests,halt
```
