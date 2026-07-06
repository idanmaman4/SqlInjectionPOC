:- module(sqlite_pdo_parser,
          [ parse_sql/2,
            parse_sql/3,
            tokenize_sql/2,
            statement_placeholders/2,
            statements_placeholders/2
          ]).

:- use_module(sqlite_pdo_lexer,
              [ tokenize_sql/2
              ]).
:- use_module(sqlite_pdo_grammar,
              [ parse_tokens/3,
                statement_placeholders/2,
                statements_placeholders/2
              ]).

/** <module> SQLite SQL parser with PDO placeholder support.

Public facade for the SQLite/PDO parser:

  - sqlite_pdo_lexer.pl handles SQL tokenization.
  - sqlite_pdo_grammar.pl handles statement grammar and AST construction.

Placeholders are returned as:

  - placeholder(positional) for ?
  - placeholder(indexed(N)) for ?NNN
  - placeholder(named(Prefix, Name)) for :name, @name, or $name
*/

%! parse_sql(+Sql:text, -Statements:list) is semidet.
%
%  Parse Sql into a list of statement AST dictionaries. Unknown statements are
%  returned as raw statement nodes unless Options contains strict(true).

parse_sql(Sql, Statements) :-
    parse_sql(Sql, Statements, []).

%! parse_sql(+Sql:text, -Statements:list, +Options:list) is semidet.
%
%  Supported options:
%
%    - strict(true): fail if a statement cannot be parsed into a known AST.

parse_sql(Sql, Statements, Options) :-
    tokenize_sql(Sql, Tokens),
    parse_tokens(Tokens, Statements, Options).
