:- module(sqlite_pdo_lexer,
          [ tokenize_sql/2
          ]).

/** <module> SQLite lexer with PDO placeholder tokens.

Tokenizes SQL for the parser. Whitespace and comments are skipped, and
placeholders inside comments or string literals remain ordinary text.
*/

%! tokenize_sql(+Sql:text, -Tokens:list) is semidet.
%
%  Tokenize SQLite SQL while ignoring whitespace and comments.

tokenize_sql(Sql, Tokens) :-
    text_codes(Sql, Codes),
    phrase(tokens(Tokens), Codes).

text_codes(Sql, Codes) :-
    string(Sql),
    !,
    string_codes(Sql, Codes).
text_codes(Sql, Codes) :-
    atom(Sql),
    !,
    atom_codes(Sql, Codes).
text_codes(Codes, Codes) :-
    is_list(Codes).

tokens(Tokens) -->
    skip_layout,
    (   eos
    ->  { Tokens = [] }
    ;   token(Token),
        !,
        { Tokens = [Token|Rest] },
        tokens(Rest)
    ).

skip_layout -->
    [C],
    { code_type(C, space) },
    !,
    skip_layout.
skip_layout -->
    "--",
    !,
    line_comment,
    skip_layout.
skip_layout -->
    "/*",
    !,
    block_comment,
    skip_layout.
skip_layout --> [].

line_comment -->
    [10],
    !.
line_comment -->
    [_],
    !,
    line_comment.
line_comment --> [].

block_comment -->
    "*/",
    !.
block_comment -->
    [_],
    !,
    block_comment.

token(Token) -->
    string_literal(Token).
token(Token) -->
    quoted_identifier(Token).
token(Token) -->
    placeholder(Token).
token(Token) -->
    number_token(Token).
token(Token) -->
    bare_identifier(Token).
token(Token) -->
    operator_token(Token).
token(Token) -->
    symbol_token(Token).

string_literal(string(String)) -->
    "'",
    string_chars(Codes),
    "'",
    { string_codes(String, Codes) }.

string_chars([39|Rest]) -->
    "''",
    !,
    string_chars(Rest).
string_chars([]) -->
    peek("'"),
    !.
string_chars([C|Rest]) -->
    [C],
    !,
    string_chars(Rest).
string_chars([]) --> [].

quoted_identifier(qid(String)) -->
    [34],
    quoted_chars(34, Codes),
    [34],
    { string_codes(String, Codes) }.
quoted_identifier(qid(String)) -->
    "`",
    quoted_chars(96, Codes),
    "`",
    { string_codes(String, Codes) }.
quoted_identifier(qid(String)) -->
    "[",
    bracket_chars(Codes),
    "]",
    { string_codes(String, Codes) }.

quoted_chars(Quote, [Quote|Rest]) -->
    [Quote, Quote],
    !,
    quoted_chars(Quote, Rest).
quoted_chars(Quote, []) -->
    peek_code(Quote),
    !.
quoted_chars(Quote, [C|Rest]) -->
    [C],
    !,
    quoted_chars(Quote, Rest).

bracket_chars([]) -->
    peek("]"),
    !.
bracket_chars([C|Rest]) -->
    [C],
    !,
    bracket_chars(Rest).

placeholder(placeholder(indexed(N))) -->
    "?",
    digits(Digits),
    { Digits \= [],
      number_codes(N, Digits)
    }.
placeholder(placeholder(positional)) -->
    "?".
placeholder(placeholder(named(PrefixAtom, Name))) -->
    [Prefix],
    { memberchk(Prefix, [0':, 0'@, 0'$]) },
    identifier_start_code(Start),
    identifier_continue_codes(Rest),
    { atom_codes(PrefixAtom, [Prefix]),
      atom_codes(Name, [Start|Rest])
    }.

number_token(number(Number)) -->
    digits(Before),
    ".",
    digits(After),
    { Before \= [],
      After \= [],
      append(Before, [0'.|After], Codes),
      number_codes(Number, Codes)
    }.
number_token(number(Number)) -->
    digits(Digits),
    { Digits \= [],
      number_codes(Number, Digits)
    }.

bare_identifier(Token) -->
    identifier_start_code(Start),
    identifier_continue_codes(Rest),
    { atom_codes(Atom, [Start|Rest]),
      downcase_atom(Atom, Lower),
      keyword_token(Lower, Atom, Token)
    }.

identifier_start_code(C) -->
    [C],
    { code_type(C, alpha) ; C =:= 0'_ }.

identifier_continue_codes([C|Rest]) -->
    [C],
    { code_type(C, alnum) ; memberchk(C, [0'_, 0'$]) },
    !,
    identifier_continue_codes(Rest).
identifier_continue_codes([]) --> [].

digits([D|Rest]) -->
    [D],
    { code_type(D, digit) },
    !,
    digits(Rest).
digits([]) --> [].

keyword_token(Lower, _Original, kw(Lower)) :-
    sqlite_keyword(Lower),
    !.
keyword_token(_Lower, Original, id(Original)).

operator_token(op('->>')) --> "->>".
operator_token(op('->')) --> "->".
operator_token(op('<=')) --> "<=".
operator_token(op('>=')) --> ">=".
operator_token(op('<>')) --> "<>".
operator_token(op('!=')) --> "!=".
operator_token(op('==')) --> "==".
operator_token(op('||')) --> "||".
operator_token(op('<<')) --> "<<".
operator_token(op('>>')) --> ">>".
operator_token(op('=')) --> "=".
operator_token(op('<')) --> "<".
operator_token(op('>')) --> ">".
operator_token(op('+')) --> "+".
operator_token(op('-')) --> "-".
operator_token(op('*')) --> "*".
operator_token(op('/')) --> "/".
operator_token(op('%')) --> "%".
operator_token(op('~')) --> "~".
operator_token(op('&')) --> "&".
operator_token(op('|')) --> "|".

symbol_token(sym('(')) --> "(".
symbol_token(sym(')')) --> ")".
symbol_token(sym(',')) --> ",".
symbol_token(sym('.')) --> ".".
symbol_token(sym(';')) --> ";".

peek(String, List, List) :-
    string_codes(String, Codes),
    append(Codes, _, List).

peek_code(Code, List, List) :-
    List = [Code|_].

eos([], []).

sqlite_keyword(abort).
sqlite_keyword(action).
sqlite_keyword(add).
sqlite_keyword(after).
sqlite_keyword(all).
sqlite_keyword(alter).
sqlite_keyword(always).
sqlite_keyword(analyze).
sqlite_keyword(and).
sqlite_keyword(as).
sqlite_keyword(asc).
sqlite_keyword(attach).
sqlite_keyword(autoincrement).
sqlite_keyword(before).
sqlite_keyword(begin).
sqlite_keyword(between).
sqlite_keyword(by).
sqlite_keyword(cascade).
sqlite_keyword(case).
sqlite_keyword(cast).
sqlite_keyword(check).
sqlite_keyword(collate).
sqlite_keyword(column).
sqlite_keyword(commit).
sqlite_keyword(conflict).
sqlite_keyword(constraint).
sqlite_keyword(create).
sqlite_keyword(cross).
sqlite_keyword(current).
sqlite_keyword(current_date).
sqlite_keyword(current_time).
sqlite_keyword(current_timestamp).
sqlite_keyword(database).
sqlite_keyword(default).
sqlite_keyword(deferrable).
sqlite_keyword(deferred).
sqlite_keyword(delete).
sqlite_keyword(desc).
sqlite_keyword(detach).
sqlite_keyword(distinct).
sqlite_keyword(do).
sqlite_keyword(drop).
sqlite_keyword(each).
sqlite_keyword(else).
sqlite_keyword(end).
sqlite_keyword(escape).
sqlite_keyword(except).
sqlite_keyword(exclude).
sqlite_keyword(exclusive).
sqlite_keyword(exists).
sqlite_keyword(explain).
sqlite_keyword(fail).
sqlite_keyword(filter).
sqlite_keyword(first).
sqlite_keyword(following).
sqlite_keyword(for).
sqlite_keyword(foreign).
sqlite_keyword(from).
sqlite_keyword(full).
sqlite_keyword(generated).
sqlite_keyword(glob).
sqlite_keyword(group).
sqlite_keyword(groups).
sqlite_keyword(having).
sqlite_keyword(if).
sqlite_keyword(ignore).
sqlite_keyword(immediate).
sqlite_keyword(in).
sqlite_keyword(index).
sqlite_keyword(indexed).
sqlite_keyword(initially).
sqlite_keyword(inner).
sqlite_keyword(insert).
sqlite_keyword(instead).
sqlite_keyword(intersect).
sqlite_keyword(into).
sqlite_keyword(is).
sqlite_keyword(isnull).
sqlite_keyword(join).
sqlite_keyword(key).
sqlite_keyword(last).
sqlite_keyword(left).
sqlite_keyword(like).
sqlite_keyword(limit).
sqlite_keyword(match).
sqlite_keyword(materialized).
sqlite_keyword(natural).
sqlite_keyword(no).
sqlite_keyword(not).
sqlite_keyword(nothing).
sqlite_keyword(notnull).
sqlite_keyword(null).
sqlite_keyword(nulls).
sqlite_keyword(of).
sqlite_keyword(offset).
sqlite_keyword(on).
sqlite_keyword(or).
sqlite_keyword(order).
sqlite_keyword(others).
sqlite_keyword(outer).
sqlite_keyword(over).
sqlite_keyword(partition).
sqlite_keyword(plan).
sqlite_keyword(pragma).
sqlite_keyword(preceding).
sqlite_keyword(primary).
sqlite_keyword(query).
sqlite_keyword(raise).
sqlite_keyword(range).
sqlite_keyword(recursive).
sqlite_keyword(references).
sqlite_keyword(regexp).
sqlite_keyword(reindex).
sqlite_keyword(release).
sqlite_keyword(rename).
sqlite_keyword(replace).
sqlite_keyword(restrict).
sqlite_keyword(returning).
sqlite_keyword(right).
sqlite_keyword(rollback).
sqlite_keyword(row).
sqlite_keyword(rows).
sqlite_keyword(savepoint).
sqlite_keyword(select).
sqlite_keyword(set).
sqlite_keyword(table).
sqlite_keyword(temp).
sqlite_keyword(temporary).
sqlite_keyword(then).
sqlite_keyword(ties).
sqlite_keyword(to).
sqlite_keyword(transaction).
sqlite_keyword(trigger).
sqlite_keyword(unbounded).
sqlite_keyword(union).
sqlite_keyword(unique).
sqlite_keyword(update).
sqlite_keyword(using).
sqlite_keyword(vacuum).
sqlite_keyword(values).
sqlite_keyword(view).
sqlite_keyword(virtual).
sqlite_keyword(when).
sqlite_keyword(where).
sqlite_keyword(window).
sqlite_keyword(with).
sqlite_keyword(without).
