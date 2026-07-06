:- module(sqlite_pdo_grammar,
          [ parse_tokens/3,
            statement_placeholders/2,
            statements_placeholders/2
          ]).

:- use_module(library(apply)).
:- use_module(library(lists)).
:- use_module(grammar_rules/common,
              [ expr/2,
                option_true/2,
                placeholders/2,
                raw_statement/2,
                split_at_top_keyword/5
              ]).
:- use_module('grammar_rules/select',
              [ parse_select/2
              ]).
:- use_module('grammar_rules/insert',
              [ parse_insert/2
              ]).
:- use_module('grammar_rules/update',
              [ parse_update/2
              ]).
:- use_module('grammar_rules/delete',
              [ parse_delete/2
              ]).

/** <module> SQLite statement grammar dispatcher.

Statement-specific grammar rules live under grammar_rules/. This module splits
token streams into statements, dispatches to the right statement grammar, and
exports the parser-facing predicates.
*/

%! parse_tokens(+Tokens:list, -Statements:list, +Options:list) is semidet.
%
%  Parse a token list into statement AST dictionaries.

parse_tokens(Tokens, Statements, Options) :-
    split_statements(Tokens, StatementTokens),
    maplist(parse_statement(Options), StatementTokens, Statements0),
    exclude(==(empty), Statements0, Statements).

%! statement_placeholders(+Statement, -Placeholders:list) is det.
%
%  Collect PDO placeholders from a parsed statement AST.

statement_placeholders(Statement, Placeholders) :-
    is_dict(Statement),
    get_dict(placeholders, Statement, Placeholders),
    !.
statement_placeholders(Statement, Placeholders) :-
    findall(Placeholder,
            sub_term(placeholder(Placeholder), Statement),
            Placeholders).

%! statements_placeholders(+Statements, -Placeholders:list) is det.
%
%  Collect PDO placeholders from a list of parsed statement ASTs.

statements_placeholders(Statements, Placeholders) :-
    maplist(statement_placeholders, Statements, Nested),
    append(Nested, Placeholders).

split_statements(Tokens, Statements) :-
    split_statements(Tokens, 0, [], [], RevStatements),
    reverse(RevStatements, Statements).

split_statements([], _Depth, Current, Acc, Statements) :-
    reverse(Current, Statement),
    add_non_empty(Statement, Acc, Statements).
split_statements([sym('(')|Rest], Depth, Current, Acc, Statements) :-
    !,
    Depth1 is Depth + 1,
    split_statements(Rest, Depth1, [sym('(')|Current], Acc, Statements).
split_statements([sym(')')|Rest], Depth, Current, Acc, Statements) :-
    !,
    Depth1 is max(0, Depth - 1),
    split_statements(Rest, Depth1, [sym(')')|Current], Acc, Statements).
split_statements([sym(';')|Rest], 0, Current, Acc, Statements) :-
    !,
    reverse(Current, Statement),
    add_non_empty(Statement, Acc, Acc1),
    split_statements(Rest, 0, [], Acc1, Statements).
split_statements([Token|Rest], Depth, Current, Acc, Statements) :-
    split_statements(Rest, Depth, [Token|Current], Acc, Statements).

add_non_empty([], Acc, Acc) :- !.
add_non_empty(Statement, Acc, [Statement|Acc]).

parse_statement(_Options, [], empty) :- !.
parse_statement(Options, Tokens, Statement) :-
    parse_known_statement(Tokens, Statement),
    !,
    (   option_true(strict, Options),
        get_dict(type, Statement, raw)
    ->  fail
    ;   true
    ).
parse_statement(Options, Tokens, Statement) :-
    (   option_true(strict, Options)
    ->  fail
    ;   raw_statement(Tokens, Statement)
    ).

parse_known_statement([kw(select)|Rest], Statement) :-
    !,
    parse_select(Rest, Statement).
parse_known_statement([kw(with)|Rest], Statement) :-
    !,
    parse_with(Rest, Statement).
parse_known_statement([kw(insert)|Rest], Statement) :-
    !,
    parse_insert(Rest, Statement).
parse_known_statement([kw(update)|Rest], Statement) :-
    !,
    parse_update(Rest, Statement).
parse_known_statement([kw(delete)|Rest], Statement) :-
    !,
    parse_delete(Rest, Statement).
parse_known_statement([kw(create)|Rest], Statement) :-
    !,
    raw_statement([kw(create)|Rest], Statement0),
    Statement = Statement0.put(type, create).
parse_known_statement([kw(drop)|Rest], Statement) :-
    !,
    raw_statement([kw(drop)|Rest], Statement0),
    Statement = Statement0.put(type, drop).
parse_known_statement([kw(alter)|Rest], Statement) :-
    !,
    raw_statement([kw(alter)|Rest], Statement0),
    Statement = Statement0.put(type, alter).
parse_known_statement([kw(pragma)|Rest], Statement) :-
    !,
    raw_statement([kw(pragma)|Rest], Statement0),
    Statement = Statement0.put(type, pragma).
parse_known_statement(Tokens, Statement) :-
    raw_statement(Tokens, Statement).

parse_with(Tokens, Statement) :-
    split_at_top_keyword(Tokens, [select, insert, update, delete], CteTokens, Keyword, BodyTokens),
    parse_known_statement([kw(Keyword)|BodyTokens], Body),
    expr(CteTokens, Ctes),
    placeholders(Tokens, Placeholders),
    Statement = statement{ type:with,
                           ctes:Ctes,
                           body:Body,
                           placeholders:Placeholders }.
