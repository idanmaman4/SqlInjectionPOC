:- module(sqlite_pdo_grammar_select,
          [ parse_select/2
          ]).

:- use_module(common,
              [ expr_list/2,
                maybe_expr/2,
                placeholders/2,
                split_at_top_keyword/5
              ]).

/** <module> SELECT statement grammar. */

parse_select(Tokens0, Statement) :-
    select_quantifier(Tokens0, Quantifier, Tokens),
    (   split_at_top_keyword(Tokens, [from], ColumnTokens, _From, FromAndTail)
    ->  split_select_tail(FromAndTail, FromTokens, WhereTokens, TailTokens),
        FromTokens \= []
    ;   ColumnTokens = Tokens,
        FromTokens = [],
        WhereTokens = [],
        TailTokens = []
    ),
    ColumnTokens \= [],
    expr_list(ColumnTokens, Columns),
    expr_list(FromTokens, From),
    maybe_expr(WhereTokens, Where),
    placeholders([kw(select)|Tokens0], Placeholders),
    Statement = statement{ type:select,
                           quantifier:Quantifier,
                           columns:Columns,
                           from:From,
                           where:Where,
                           tail:TailTokens,
                           placeholders:Placeholders }.

select_quantifier([kw(distinct)|Rest], distinct, Rest) :- !.
select_quantifier([kw(all)|Rest], all, Rest) :- !.
select_quantifier(Tokens, default, Tokens).

split_select_tail(Tokens, FromTokens, WhereTokens, TailTokens) :-
    (   split_at_top_keyword(Tokens, [where], FromTokens0, _Where, AfterWhere)
    ->  FromTokens = FromTokens0,
        (   split_at_top_keyword(AfterWhere,
                                 [group, having, order, limit, offset, union, except, intersect, window],
                                 WhereTokens,
                                 TailKeyword,
                                 TailRest)
        ->  TailTokens = [kw(TailKeyword)|TailRest]
        ;   WhereTokens = AfterWhere,
            TailTokens = []
        )
    ;   split_at_top_keyword(Tokens,
                             [group, having, order, limit, offset, union, except, intersect, window],
                             FromTokens,
                             TailKeyword,
                             TailRest)
    ->  WhereTokens = [],
        TailTokens = [kw(TailKeyword)|TailRest]
    ;   FromTokens = Tokens,
        WhereTokens = [],
        TailTokens = []
    ).
split_select_tail(_Tokens, [], [], []) :-
    fail.
