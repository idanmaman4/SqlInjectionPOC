# Expression Grammar

Implemented mostly in [grammar_rules/common.pl](../../grammar_rules/common.pl).

Expressions are validated and stored as:

$$
\operatorname{expr}\{\operatorname{tokens}:T,\operatorname{placeholders}:P,\operatorname{ast}:A\}
$$

## Expression Items And Aliases

Expression items are used for select lists, column lists, value rows, and
similar comma-separated regions.

$$
\langle expressionList \rangle ::= \langle expressionItem \rangle
  (\,\texttt{","}\ \langle expressionItem \rangle\,)^{*}
$$

$$
\langle expressionItem \rangle ::=
  \langle expression \rangle
  \mid \langle expression \rangle\ \texttt{"AS"}\ \langle name \rangle
  \mid \langle expression \rangle\ \langle name \rangle
$$

Alias AST:

$$
\operatorname{alias}(ExpressionAst, Alias)
$$

## Operator Precedence

The expression grammar is implemented from lowest to highest precedence:

$$
\langle expression \rangle ::= \langle orExpression \rangle
$$

$$
\langle orExpression \rangle ::= \langle andExpression \rangle
  (\,\texttt{"OR"}\ \langle andExpression \rangle\,)^{*}
$$

$$
\langle andExpression \rangle ::= \langle notExpression \rangle
  (\,\texttt{"AND"}\ \langle notExpression \rangle\,)^{*}
$$

$$
\langle notExpression \rangle ::= [\texttt{"NOT"}]\ \langle comparisonExpression \rangle
$$

$$
\langle comparisonExpression \rangle ::=
  \langle additiveExpression \rangle\ [\langle comparisonTail \rangle]
$$

$$
\langle additiveExpression \rangle ::=
  \langle multiplicativeExpression \rangle
  ((\texttt{"+"} \mid \texttt{"-"} \mid \texttt{"||"})
    \langle multiplicativeExpression \rangle)^{*}
$$

$$
\langle multiplicativeExpression \rangle ::=
  \langle unaryExpression \rangle
  ((\texttt{"*"} \mid \texttt{"/"} \mid \texttt{"%"} \mid
    \texttt{"&"} \mid \texttt{"|"} \mid \texttt{"<<"} \mid \texttt{">>"})
    \langle unaryExpression \rangle)^{*}
$$

$$
\langle unaryExpression \rangle ::=
  (\texttt{"+"} \mid \texttt{"-"} \mid \texttt{"~"})\langle unaryExpression \rangle
  \mid \langle primaryExpression \rangle
$$

## Comparison Tail

$$
\langle comparisonTail \rangle ::=
  \langle comparisonOperator \rangle\ \langle additiveExpression \rangle
  \mid \texttt{"IS"}\ \texttt{"NULL"}
  \mid \texttt{"IS"}\ \texttt{"NOT"}\ \texttt{"NULL"}
  \mid \texttt{"LIKE"}\ \langle additiveExpression \rangle
  \mid \texttt{"NOT"}\ \texttt{"LIKE"}\ \langle additiveExpression \rangle
  \mid \texttt{"IN"}\ \langle parenthesizedRhs \rangle
  \mid \texttt{"NOT"}\ \texttt{"IN"}\ \langle parenthesizedRhs \rangle
  \mid \texttt{"BETWEEN"}\ \langle additiveExpression \rangle\ \texttt{"AND"}\ \langle additiveExpression \rangle
$$

$$
\langle comparisonOperator \rangle ::=
  \texttt{"="} \mid \texttt{"<"} \mid \texttt{">"} \mid
  \texttt{"<="} \mid \texttt{">="} \mid \texttt{"<>"} \mid
  \texttt{"!="} \mid \texttt{"=="}
$$

## Primary Expressions

$$
\langle primaryExpression \rangle ::=
  \texttt{"*"}
  \mid \langle number \rangle
  \mid \langle string \rangle
  \mid \langle placeholder \rangle
  \mid \texttt{"NULL"}
  \mid \texttt{"("}\ \langle expression \rangle\ \texttt{")"}
  \mid \langle subquery \rangle
  \mid \langle functionCall \rangle
  \mid \langle namePath \rangle
$$

## Function Calls

$$
\langle functionCall \rangle ::=
  \langle namePath \rangle\ \texttt{"("}\ [\langle functionArgs \rangle]\ \texttt{")"}
$$

$$
\langle functionArgs \rangle ::= \texttt{"*"} \mid \langle expressionList \rangle
$$

## Names

$$
\langle namePath \rangle ::= \langle name \rangle
  (\,\texttt{"."}\ \langle name \rangle\,)^{*}
$$

$$
\langle name \rangle ::= \langle identifier \rangle \mid \langle quotedIdentifier \rangle
$$

The lexer also accepts these current-time keywords as names:

$$
\texttt{"CURRENT\_DATE"} \mid \texttt{"CURRENT\_TIME"} \mid \texttt{"CURRENT\_TIMESTAMP"}
$$

## Subqueries And IN Lists

$$
\langle subquery \rangle ::= \texttt{"("}\ \langle selectStatement \rangle\ \texttt{")"}
$$

$$
\langle parenthesizedRhs \rangle ::= \langle subquery \rangle
  \mid \texttt{"("}\ \langle expressionList \rangle\ \texttt{")"}
$$
