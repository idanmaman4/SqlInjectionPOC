:- module(sqlite_pdo_grammar_common,
          [ raw_statement/2,
            expr_list/2,
            maybe_expr/2,
            expr/2,
            token_expr/2,
            atomics_or_none/2,
            placeholders/2,
            split_at_top_keyword/5,
            split_at_top_op/4,
            split_top_commas/2,
            take_paren_body/3,
            option_true/2
          ]).

/** <module> Shared SQLite grammar helpers.

These predicates operate on lexer tokens and are reused by statement-specific
grammar modules.
*/

raw_statement(Tokens, statement{type:raw,
                                tokens:Tokens,
                                placeholders:Placeholders}) :-
    placeholders(Tokens, Placeholders).

expr_list([], []) :- !.
expr_list(Tokens, Exprs) :-
    split_top_commas(Tokens, Chunks),
    Chunks \= [],
    maplist(expr_item, Chunks, Exprs).

maybe_expr([], none) :- !.
maybe_expr(Tokens, Expr) :-
    expr(Tokens, Expr).

expr(Tokens, expr{tokens:Tokens, placeholders:Placeholders, ast:Ast}) :-
    Tokens \= [],
    phrase(sql_expr(Ast), Tokens),
    placeholders(Tokens, Placeholders).

token_expr(Tokens, Expr) :-
    expr(Tokens, Expr).

atomics_or_none([], none) :- !.
atomics_or_none(Exprs, Exprs).

placeholders(Tokens, Placeholders) :-
    findall(Placeholder,
            member(placeholder(Placeholder), Tokens),
            Placeholders).

expr_item(Tokens, Expr) :-
    split_at_top_keyword(Tokens, [as], ExprTokens, _As, [AliasToken]),
    name_token(AliasToken, Alias),
    !,
    expr(ExprTokens, Base),
    Expr = Base.put(ast, alias(Base.ast, Alias)).
expr_item(Tokens, Expr) :-
    append(ExprTokens, [AliasToken], Tokens),
    ExprTokens \= [],
    name_token(AliasToken, Alias),
    expr(ExprTokens, Base),
    !,
    Expr = Base.put(ast, alias(Base.ast, Alias)).
expr_item(Tokens, Expr) :-
    expr(Tokens, Expr).

sql_expr(Ast) -->
    or_expr(Ast).

or_expr(Ast) -->
    and_expr(Left),
    or_tail(Left, Ast).

or_tail(Left, Ast) -->
    [kw(or)],
    !,
    and_expr(Right),
    or_tail(binary(or, Left, Right), Ast).
or_tail(Ast, Ast) --> [].

and_expr(Ast) -->
    not_expr(Left),
    and_tail(Left, Ast).

and_tail(Left, Ast) -->
    [kw(and)],
    !,
    not_expr(Right),
    and_tail(binary(and, Left, Right), Ast).
and_tail(Ast, Ast) --> [].

not_expr(unary(not, Expr)) -->
    [kw(not)],
    !,
    not_expr(Expr).
not_expr(Ast) -->
    comparison_expr(Ast).

comparison_expr(Ast) -->
    additive_expr(Left),
    comparison_tail(Left, Ast).

comparison_tail(Left, binary(Op, Left, Right)) -->
    comparison_operator(Op),
    !,
    additive_expr(Right).
comparison_tail(Left, is_null(Left)) -->
    [kw(is), kw(null)],
    !.
comparison_tail(Left, is_not_null(Left)) -->
    [kw(is), kw(not), kw(null)],
    !.
comparison_tail(Left, like(Left, Right)) -->
    [kw(like)],
    !,
    additive_expr(Right).
comparison_tail(Left, not_like(Left, Right)) -->
    [kw(not), kw(like)],
    !,
    additive_expr(Right).
comparison_tail(Left, in(Left, Rhs)) -->
    [kw(in)],
    !,
    parenthesized_rhs(Rhs).
comparison_tail(Left, not_in(Left, Rhs)) -->
    [kw(not), kw(in)],
    !,
    parenthesized_rhs(Rhs).
comparison_tail(Left, between(Left, Low, High)) -->
    [kw(between)],
    !,
    additive_expr(Low),
    [kw(and)],
    additive_expr(High).
comparison_tail(Ast, Ast) --> [].

comparison_operator(Op) -->
    [op(Op)],
    { memberchk(Op, ['=', '<', '>', '<=', '>=', '<>', '!=', '==']) }.

additive_expr(Ast) -->
    multiplicative_expr(Left),
    additive_tail(Left, Ast).

additive_tail(Left, Ast) -->
    [op(Op)],
    { memberchk(Op, ['+', '-', '||']) },
    !,
    multiplicative_expr(Right),
    additive_tail(binary(Op, Left, Right), Ast).
additive_tail(Ast, Ast) --> [].

multiplicative_expr(Ast) -->
    unary_expr(Left),
    multiplicative_tail(Left, Ast).

multiplicative_tail(Left, Ast) -->
    [op(Op)],
    { memberchk(Op, ['*', '/', '%', '&', '|', '<<', '>>']) },
    !,
    unary_expr(Right),
    multiplicative_tail(binary(Op, Left, Right), Ast).
multiplicative_tail(Ast, Ast) --> [].

unary_expr(unary(Op, Expr)) -->
    [op(Op)],
    { memberchk(Op, ['+', '-', '~']) },
    !,
    unary_expr(Expr).
unary_expr(Ast) -->
    primary_expr(Ast).

primary_expr(star) -->
    [op('*')],
    !.
primary_expr(literal(Number)) -->
    [number(Number)],
    !.
primary_expr(literal(String)) -->
    [string(String)],
    !.
primary_expr(placeholder(Placeholder)) -->
    [placeholder(Placeholder)],
    !.
primary_expr(literal(null)) -->
    [kw(null)],
    !.
primary_expr(subquery(Statement), In, Out) :-
    In = [sym('(')|Rest],
    take_paren_body(Rest, Body, Out),
    Body = [kw(select)|SelectTokens],
    sqlite_pdo_grammar_select:parse_select(SelectTokens, Statement),
    !.
primary_expr(group(Expr)) -->
    [sym('(')],
    sql_expr(Expr),
    [sym(')')],
    !.
primary_expr(Ast, In, Out) :-
    name_path(Name, In, AfterName),
    (   AfterName = [sym('(')|AfterOpen]
    ->  take_paren_body(AfterOpen, ArgsTokens, Out),
        parse_function_args(ArgsTokens, Args),
        Ast = call(Name, Args)
    ;   Out = AfterName,
        Ast = name(Name)
    ).

parenthesized_rhs(subquery(Statement), In, Out) :-
    In = [sym('(')|Rest],
    take_paren_body(Rest, Body, Out),
    Body = [kw(select)|SelectTokens],
    sqlite_pdo_grammar_select:parse_select(SelectTokens, Statement),
    !.
parenthesized_rhs(list(Exprs), In, Out) :-
    In = [sym('(')|Rest],
    take_paren_body(Rest, Body, Out),
    expr_list(Body, Exprs).

parse_function_args([], []) :- !.
parse_function_args([op('*')], [star]) :- !.
parse_function_args(Tokens, Args) :-
    expr_list(Tokens, Args).

name_path(Name, In, Out) :-
    name_token_dcg(First, In, Rest),
    name_path_tail(First, Name, Rest, Out).

name_path_tail(Acc, Name, [sym('.'), Token|Rest], Out) :-
    name_token(Token, Part),
    !,
    name_path_tail(qualified(Acc, Part), Name, Rest, Out).
name_path_tail(Name, Name, Out, Out).

name_token_dcg(Name) -->
    [Token],
    { name_token(Token, Name) }.

name_token(id(Name), Name).
name_token(qid(Name), Name).
name_token(kw(current_date), current_date).
name_token(kw(current_time), current_time).
name_token(kw(current_timestamp), current_timestamp).

split_at_top_keyword(Tokens, Keywords, Before, Keyword, After) :-
    split_at_top_keyword(Tokens, Keywords, 0, [], Before, Keyword, After).

split_at_top_keyword([sym('(')|Rest], Keywords, Depth, Acc, Before, Keyword, After) :-
    !,
    Depth1 is Depth + 1,
    split_at_top_keyword(Rest, Keywords, Depth1, [sym('(')|Acc], Before, Keyword, After).
split_at_top_keyword([sym(')')|Rest], Keywords, Depth, Acc, Before, Keyword, After) :-
    !,
    Depth1 is max(0, Depth - 1),
    split_at_top_keyword(Rest, Keywords, Depth1, [sym(')')|Acc], Before, Keyword, After).
split_at_top_keyword([kw(Keyword)|Rest], Keywords, 0, Acc, Before, Keyword, Rest) :-
    memberchk(Keyword, Keywords),
    !,
    reverse(Acc, Before).
split_at_top_keyword([Token|Rest], Keywords, Depth, Acc, Before, Keyword, After) :-
    split_at_top_keyword(Rest, Keywords, Depth, [Token|Acc], Before, Keyword, After).

split_at_top_op(Tokens, Operator, Before, After) :-
    split_at_top_op(Tokens, Operator, 0, [], Before, After).

split_at_top_op([sym('(')|Rest], Operator, Depth, Acc, Before, After) :-
    !,
    Depth1 is Depth + 1,
    split_at_top_op(Rest, Operator, Depth1, [sym('(')|Acc], Before, After).
split_at_top_op([sym(')')|Rest], Operator, Depth, Acc, Before, After) :-
    !,
    Depth1 is max(0, Depth - 1),
    split_at_top_op(Rest, Operator, Depth1, [sym(')')|Acc], Before, After).
split_at_top_op([op(Operator)|Rest], Operator, 0, Acc, Before, Rest) :-
    !,
    reverse(Acc, Before).
split_at_top_op([Token|Rest], Operator, Depth, Acc, Before, After) :-
    split_at_top_op(Rest, Operator, Depth, [Token|Acc], Before, After).

split_top_commas(Tokens, Chunks) :-
    split_top_commas(Tokens, 0, [], [], Chunks).

split_top_commas([], _Depth, Current, Acc, Chunks) :-
    reverse(Current, Chunk),
    reverse([Chunk|Acc], Chunks0),
    exclude(==([]), Chunks0, Chunks).
split_top_commas([sym('(')|Rest], Depth, Current, Acc, Chunks) :-
    !,
    Depth1 is Depth + 1,
    split_top_commas(Rest, Depth1, [sym('(')|Current], Acc, Chunks).
split_top_commas([sym(')')|Rest], Depth, Current, Acc, Chunks) :-
    !,
    Depth1 is max(0, Depth - 1),
    split_top_commas(Rest, Depth1, [sym(')')|Current], Acc, Chunks).
split_top_commas([sym(',')|Rest], 0, Current, Acc, Chunks) :-
    !,
    reverse(Current, Chunk),
    split_top_commas(Rest, 0, [], [Chunk|Acc], Chunks).
split_top_commas([Token|Rest], Depth, Current, Acc, Chunks) :-
    split_top_commas(Rest, Depth, [Token|Current], Acc, Chunks).

take_paren_body(Tokens, Body, After) :-
    take_paren_body(Tokens, 0, [], Body, After).

take_paren_body([sym(')')|Rest], 0, Acc, Body, Rest) :-
    !,
    reverse(Acc, Body).
take_paren_body([sym('(')|Rest], Depth, Acc, Body, After) :-
    !,
    Depth1 is Depth + 1,
    take_paren_body(Rest, Depth1, [sym('(')|Acc], Body, After).
take_paren_body([sym(')')|Rest], Depth, Acc, Body, After) :-
    Depth > 0,
    !,
    Depth1 is Depth - 1,
    take_paren_body(Rest, Depth1, [sym(')')|Acc], Body, After).
take_paren_body([Token|Rest], Depth, Acc, Body, After) :-
    take_paren_body(Rest, Depth, [Token|Acc], Body, After).

option_true(Name, Options) :-
    Term =.. [Name, true],
    memberchk(Term, Options).
