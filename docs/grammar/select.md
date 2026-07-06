# SELECT Grammar

Implemented in [grammar_rules/select.pl](../../grammar_rules/select.pl).

## SELECT Statement

$$
\langle selectStatement \rangle ::=
  \texttt{"SELECT"}\ [\langle selectQuantifier \rangle]\ \langle resultColumns \rangle\
  [\texttt{"FROM"}\ \langle fromList \rangle]\
  [\texttt{"WHERE"}\ \langle expression \rangle]\
  [\langle selectTail \rangle]
$$

The result column list must be non-empty. If `FROM` appears, the `fromList`
must be non-empty.

## Quantifier

$$
\langle selectQuantifier \rangle ::= \texttt{"DISTINCT"} \mid \texttt{"ALL"}
$$

## Result Columns And FROM

$$
\langle resultColumns \rangle ::= \langle expressionItem \rangle
  (\,\texttt{","}\ \langle expressionItem \rangle\,)^{*}
$$

$$
\langle fromList \rangle ::= \langle expressionItem \rangle
  (\,\texttt{","}\ \langle expressionItem \rangle\,)^{*}
$$

## Tail

Tail clauses are currently preserved as tokens after the first recognized tail
keyword.

$$
\langle selectTail \rangle ::=
  (\texttt{"GROUP"} \mid \texttt{"HAVING"} \mid \texttt{"ORDER"} \mid
   \texttt{"LIMIT"} \mid \texttt{"OFFSET"} \mid \texttt{"UNION"} \mid
   \texttt{"EXCEPT"} \mid \texttt{"INTERSECT"} \mid \texttt{"WINDOW"})
  \langle token \rangle^{*}
$$
