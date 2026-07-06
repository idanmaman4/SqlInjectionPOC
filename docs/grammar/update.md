# UPDATE Grammar

Implemented in [grammar_rules/update.pl](../../grammar_rules/update.pl).

## UPDATE Statement

$$
\langle updateStatement \rangle ::=
  \texttt{"UPDATE"}\ \langle tableExpr \rangle\
  \texttt{"SET"}\ \langle assignmentList \rangle\
  [\texttt{"WHERE"}\ \langle expression \rangle]\
  [\langle updateTail \rangle]
$$

$$
\langle tableExpr \rangle ::= \langle expression \rangle
$$

## Assignments

$$
\langle assignmentList \rangle ::= \langle assignment \rangle
  (\,\texttt{","}\ \langle assignment \rangle\,)^{*}
$$

$$
\langle assignment \rangle ::= \langle expression \rangle\ \texttt{"="}\ \langle expression \rangle
$$

## Tail

Tail clauses are preserved as tokens after the first recognized tail keyword.

$$
\langle updateTail \rangle ::=
  (\texttt{"RETURNING"} \mid \texttt{"ORDER"} \mid \texttt{"LIMIT"})
  \langle token \rangle^{*}
$$
