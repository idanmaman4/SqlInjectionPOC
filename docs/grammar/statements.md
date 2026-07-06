# Statement Grammar

Implemented in [sqlite_pdo_grammar.pl](../../sqlite_pdo_grammar.pl).

## Statement List

Statements are split on semicolons that are not nested inside parentheses.

$$
\langle statementList \rangle ::= \langle statement \rangle
  (\,\texttt{";"}\ \langle statement \rangle\,)^{*}
  [\texttt{";"}]
$$

## Statement Dispatch

$$
\langle statement \rangle ::=
  \langle selectStatement \rangle
  \mid \langle withStatement \rangle
  \mid \langle insertStatement \rangle
  \mid \langle updateStatement \rangle
  \mid \langle deleteStatement \rangle
  \mid \langle schemaOrUtilityStatement \rangle
$$

Schema and utility statements are preserved as raw token statements:

$$
\langle schemaOrUtilityStatement \rangle ::=
  (\texttt{"CREATE"} \mid \texttt{"DROP"} \mid \texttt{"ALTER"} \mid \texttt{"PRAGMA"})
  \langle token \rangle^{*}
$$

In non-strict mode, unknown statements also become raw token statements.
In `strict(true)` mode, unknown statements fail.

## WITH

The current `WITH` support validates the CTE prefix as an expression-like token
region and recursively parses the first statement keyword that follows it.

$$
\langle withStatement \rangle ::=
  \texttt{"WITH"}\ \langle cteTokens \rangle\
  (\langle selectStatement \rangle
    \mid \langle insertStatement \rangle
    \mid \langle updateStatement \rangle
    \mid \langle deleteStatement \rangle)
$$

$$
\langle cteTokens \rangle ::= \langle expression \rangle
$$
