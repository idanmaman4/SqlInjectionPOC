:- module(sqlite_pdo_grammar_insert,
          [ parse_insert/2
          ]).

:- use_module(common,
              [ atomics_or_none/2,
                expr_list/2,
                placeholders/2,
                raw_statement/2,
                split_at_top_keyword/5,
                take_paren_body/3,
                token_expr/2
              ]).

/** <module> INSERT statement grammar. */

parse_insert(Tokens, Statement) :-
    split_at_top_keyword(Tokens, [into], PrefixTokens, _Into, AfterInto),
    !,
    AfterInto = [TableToken|AfterTable],
    parse_insert_columns(AfterTable, ColumnTokens, AfterColumns),
    (   split_at_top_keyword(AfterColumns, [values], BeforeValues, _Values, ValueTokens)
    ->  parse_values(ValueTokens, Values),
        Body = values{ prefix:BeforeValues, rows:Values }
    ;   Body = body{ tokens:AfterColumns }
    ),
    token_expr([TableToken], Table),
    atomics_or_none(ColumnTokens, Columns),
    placeholders([kw(insert)|Tokens], Placeholders),
    Statement = statement{ type:insert,
                           prefix:PrefixTokens,
                           table:Table,
                           columns:Columns,
                           body:Body,
                           placeholders:Placeholders }.
parse_insert(Tokens, Statement) :-
    raw_statement([kw(insert)|Tokens], Statement0),
    Statement = Statement0.put(type, insert).

parse_insert_columns([sym('(')|Rest], Columns, AfterColumns) :-
    take_paren_body(Rest, Body, AfterColumns),
    !,
    expr_list(Body, Columns).
parse_insert_columns(Tokens, [], Tokens).

parse_values(Tokens, Rows) :-
    parse_value_rows(Tokens, Rows),
    !.
parse_values(Tokens, [expr{tokens:Tokens, placeholders:Placeholders}]) :-
    placeholders(Tokens, Placeholders).

parse_value_rows([], []).
parse_value_rows([sym('(')|Rest], [Row|Rows]) :-
    take_paren_body(Rest, Body, AfterParen),
    expr_list(Body, Row),
    consume_optional_comma(AfterParen, AfterComma),
    parse_value_rows(AfterComma, Rows).

consume_optional_comma([sym(',')|Rest], Rest) :- !.
consume_optional_comma(Tokens, Tokens).
