:- begin_tests(sqlite_pdo_parser).

:- use_module(sqlite_pdo_parser).

test(tokenize_pdo_placeholders_outside_strings_and_comments) :-
    Sql = "SELECT '?' AS literal, ?2, :name, @token, $tenant -- ? ignored\n",
    tokenize_sql(Sql, Tokens),
    assertion(memberchk(string("?"), Tokens)),
    assertion(\+ memberchk(placeholder(positional), Tokens)),
    assertion(include_placeholders(Tokens,
                                   [ indexed(2),
                                     named(':', name),
                                     named('@', token),
                                     named('$', tenant)
                                   ])).

test(parse_select_with_where_placeholders) :-
    Sql = "SELECT id, name FROM users WHERE id = ? AND email = :email",
    parse_sql(Sql, [Statement]),
    assertion(Statement.type == select),
    assertion(Statement.quantifier == default),
    assertion(length(Statement.columns, 2)),
    assertion(length(Statement.from, 1)),
    statement_placeholders(Statement, Placeholders),
    assertion(Placeholders == [positional, named(':', email)]),
    assertion(Statement.where.placeholders == [positional, named(':', email)]).

test(parse_multiple_statements) :-
    Sql = "SELECT 1; UPDATE users SET name = @name WHERE id = ?1;",
    parse_sql(Sql, Statements),
    assertion(maplist_type(Statements, [select, update])),
    statements_placeholders(Statements, Placeholders),
    assertion(Placeholders == [named('@', name), indexed(1)]).

test(parse_insert_values) :-
    Sql = "INSERT INTO users (name, email) VALUES (:name, ?)",
    parse_sql(Sql, [Statement]),
    assertion(Statement.type == insert),
    get_dict(table, Statement, Table),
    assertion(Table.tokens == [id(users)]),
    assertion(length(Statement.columns, 2)),
    get_dict(body, Statement, Body),
    get_dict(rows, Body, Rows),
    Rows = [[NameExpr, PositionalExpr]],
    assertion(NameExpr.tokens == [placeholder(named(':', name))]),
    assertion(NameExpr.placeholders == [named(':', name)]),
    assertion(NameExpr.ast == placeholder(named(':', name))),
    assertion(PositionalExpr.tokens == [placeholder(positional)]),
    assertion(PositionalExpr.placeholders == [positional]),
    assertion(PositionalExpr.ast == placeholder(positional)).

test(parse_update_assignments) :-
    Sql = "UPDATE users SET name = :name, active = ? WHERE id = ?2",
    parse_sql(Sql, [Statement]),
    assertion(Statement.type == update),
    assertion(length(Statement.assignments, 2)),
    assertion(Statement.placeholders == [named(':', name), positional, indexed(2)]),
    assertion(Statement.where.tokens == [id(id), op(=), placeholder(indexed(2))]).

test(parse_delete) :-
    Sql = "DELETE FROM sessions WHERE expires_at < :now RETURNING id",
    parse_sql(Sql, [Statement]),
    assertion(Statement.type == delete),
    assertion(Statement.where.placeholders == [named(':', now)]),
    assertion(Statement.tail == [kw(returning), id(id)]).

test(quoted_identifiers_and_escaped_strings) :-
    Sql = "SELECT \"weird name\", 'it''s ok' FROM [user table] WHERE `key` = $key",
    parse_sql(Sql, [Statement]),
    Statement.columns = [QuotedName, EscapedString],
    assertion(QuotedName.tokens == [qid("weird name")]),
    assertion(QuotedName.ast == name("weird name")),
    assertion(EscapedString.tokens == [string("it's ok")]),
    assertion(EscapedString.ast == literal("it's ok")),
    Statement.from = [Table],
    assertion(Table.tokens == [qid("user table")]),
    assertion(Table.ast == name("user table")),
    assertion(Statement.where.placeholders == [named('$', key)]).

test(strict_accepts_nested_subquery) :-
    Sql = "SELECT * FROM users WHERE id IN (SELECT user_id FROM orders WHERE total > ?)",
    parse_sql(Sql, [Statement], [strict(true)]),
    assertion(Statement.type == select),
    assertion(Statement.where.placeholders == [positional]).

test(strict_rejects_missing_select_list, [fail]) :-
    parse_sql("SELECT FROM users WHERE id = ?", _Statements, [strict(true)]).

test(strict_rejects_missing_from_target, [fail]) :-
    parse_sql("SELECT id FROM", _Statements, [strict(true)]).

test(strict_rejects_bad_where_expression, [fail]) :-
    parse_sql("SELECT id FROM users WHERE = =", _Statements, [strict(true)]).

test(strict_rejects_bad_update_assignment, [fail]) :-
    parse_sql("UPDATE users SET name = WHERE id = ?", _Statements, [strict(true)]).

test(strict_accepts_functions_and_aliases) :-
    Sql = "SELECT count(*) AS total, lower(email) domain FROM users WHERE email LIKE :pattern",
    parse_sql(Sql, [Statement], [strict(true)]),
    assertion(Statement.type == select),
    assertion(Statement.placeholders == [named(':', pattern)]),
    Statement.columns = [Count, Lower],
    assertion(Count.ast == alias(call(count, [star]), total)),
    assertion(Lower.ast == alias(call(lower, [expr{ast:name(email), placeholders:[], tokens:[id(email)]}]), domain)).

test(raw_fallback_for_unknown_statement) :-
    parse_sql("VACUUM main", [Statement]),
    assertion(Statement.type == raw),
    assertion(Statement.tokens == [kw(vacuum), id(main)]).

test(strict_rejects_unknown_statement, [fail]) :-
    parse_sql("VACUUM main", _Statements, [strict(true)]).

include_placeholders(Tokens, Placeholders) :-
    findall(Placeholder,
            member(placeholder(Placeholder), Tokens),
            Placeholders).

maplist_type([], []).
maplist_type([Statement|Statements], [Type|Types]) :-
    Statement.type == Type,
    maplist_type(Statements, Types).

:- end_tests(sqlite_pdo_parser).
