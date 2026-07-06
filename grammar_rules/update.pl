:- module(sqlite_pdo_grammar_update,
          [ parse_update/2
          ]).

:- use_module(common,
              [ expr/2,
                maybe_expr/2,
                placeholders/2,
                raw_statement/2,
                split_at_top_keyword/5,
                split_at_top_op/4,
                split_top_commas/2
              ]).

/** <module> UPDATE statement grammar. */

parse_update(Tokens, Statement) :-
    split_at_top_keyword(Tokens, [set], TableTokens, _Set, AfterSet),
    !,
    split_update_tail(AfterSet, AssignmentTokens, WhereTokens, TailTokens),
    expr(TableTokens, Table),
    parse_assignments(AssignmentTokens, Assignments),
    maybe_expr(WhereTokens, Where),
    placeholders([kw(update)|Tokens], Placeholders),
    Statement = statement{ type:update,
                           table:Table,
                           assignments:Assignments,
                           where:Where,
                           tail:TailTokens,
                           placeholders:Placeholders }.
parse_update(Tokens, Statement) :-
    raw_statement([kw(update)|Tokens], Statement0),
    Statement = Statement0.put(type, update).

split_update_tail(Tokens, AssignmentTokens, WhereTokens, TailTokens) :-
    (   split_at_top_keyword(Tokens, [where], AssignmentTokens, _Where, AfterWhere)
    ->  (   split_at_top_keyword(AfterWhere, [returning, order, limit], WhereTokens, TailKeyword, TailRest)
        ->  TailTokens = [kw(TailKeyword)|TailRest]
        ;   WhereTokens = AfterWhere,
            TailTokens = []
        )
    ;   split_at_top_keyword(Tokens, [returning, order, limit], AssignmentTokens, TailKeyword, TailRest)
    ->  WhereTokens = [],
        TailTokens = [kw(TailKeyword)|TailRest]
    ;   AssignmentTokens = Tokens,
        WhereTokens = [],
        TailTokens = []
    ).

parse_assignments(Tokens, Assignments) :-
    split_top_commas(Tokens, Chunks),
    maplist(parse_assignment, Chunks, Assignments).

parse_assignment(Tokens, assignment{target:Target, value:Value}) :-
    split_at_top_op(Tokens, '=', TargetTokens, ValueTokens),
    !,
    expr(TargetTokens, Target),
    expr(ValueTokens, Value).
parse_assignment(Tokens, Expr) :-
    expr(Tokens, Expr).
