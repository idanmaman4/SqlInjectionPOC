# INSERT Grammar

Implemented in [grammar_rules/insert.pl](../../grammar_rules/insert.pl).

## INSERT Statement

$$
\langle insertStatement \rangle ::=
  \texttt{"INSERT"}\ \langle insertPrefix \rangle\
  \texttt{"INTO"}\ \langle tableName \rangle\
  [\langle columnList \rangle]\
  \langle insertBody \rangle
$$

The parser keeps tokens before `INTO` as `insertPrefix`, which permits common
SQLite forms such as `INSERT OR REPLACE`.

$$
\langle insertPrefix \rangle ::= \langle token \rangle^{*}
$$

$$
\langle tableName \rangle ::= \langle expression \rangle
$$

## Columns

$$
\langle columnList \rangle ::=
  \texttt{"("}\ \langle expressionItem \rangle
  (\,\texttt{","}\ \langle expressionItem \rangle\,)^{*}\ \texttt{")"}
$$

## Body

$$
\langle insertBody \rangle ::= \langle valuesBody \rangle \mid \langle rawInsertBody \rangle
$$

$$
\langle valuesBody \rangle ::=
  \texttt{"VALUES"}\ \langle valueRow \rangle
  (\,\texttt{","}\ \langle valueRow \rangle\,)^{*}
$$

$$
\langle valueRow \rangle ::=
  \texttt{"("}\ \langle expressionItem \rangle
  (\,\texttt{","}\ \langle expressionItem \rangle\,)^{*}\ \texttt{")"}
$$

If the body is not a `VALUES` body, the remaining tokens are preserved.

$$
\langle rawInsertBody \rangle ::= \langle token \rangle^{*}
$$
