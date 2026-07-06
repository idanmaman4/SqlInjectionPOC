# DELETE Grammar

Implemented in [grammar_rules/delete.pl](../../grammar_rules/delete.pl).

## DELETE Statement

$$
\langle deleteStatement \rangle ::=
  \texttt{"DELETE"}\ [\texttt{"FROM"}]\ \langle fromExpr \rangle\
  [\texttt{"WHERE"}\ \langle expression \rangle]\
  [\langle deleteTail \rangle]
$$

$$
\langle fromExpr \rangle ::= \langle expression \rangle
$$

## Tail

Tail clauses are preserved as tokens after the first recognized tail keyword.

$$
\langle deleteTail \rangle ::=
  (\texttt{"RETURNING"} \mid \texttt{"ORDER"} \mid \texttt{"LIMIT"})
  \langle token \rangle^{*}
$$
