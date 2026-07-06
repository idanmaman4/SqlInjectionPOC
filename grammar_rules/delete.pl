:- module(sqlite_pdo_grammar_delete,
          [ parse_delete/2
          ]).

:- use_module(common,
              [ expr/2,
                maybe_expr/2,
                placeholders/2,
                split_at_top_keyword/5
              ]).

/** <module> DELETE statement grammar. */

parse_delete(Tokens, Statement) :-
    (   Tokens = [kw(from)|Rest]
    ->  true
    ;   Rest = Tokens
    ),
    split_delete_tail(Rest, FromTokens, WhereTokens, TailTokens),
    expr(FromTokens, From),
    maybe_expr(WhereTokens, Where),
    placeholders([kw(delete)|Tokens], Placeholders),
    Statement = statement{ type:delete,
                           from:From,
                           where:Where,
                           tail:TailTokens,
                           placeholders:Placeholders }.

split_delete_tail(Tokens, FromTokens, WhereTokens, TailTokens) :-
    (   split_at_top_keyword(Tokens, [where], FromTokens, _Where, AfterWhere)
    ->  (   split_at_top_keyword(AfterWhere, [returning, order, limit], WhereTokens, TailKeyword, TailRest)
        ->  TailTokens = [kw(TailKeyword)|TailRest]
        ;   WhereTokens = AfterWhere,
            TailTokens = []
        )
    ;   split_at_top_keyword(Tokens, [returning, order, limit], FromTokens, TailKeyword, TailRest)
    ->  WhereTokens = [],
        TailTokens = [kw(TailKeyword)|TailRest]
    ;   FromTokens = Tokens,
        WhereTokens = [],
        TailTokens = []
    ).
