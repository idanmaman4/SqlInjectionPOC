# Token Grammar

Implemented in [sqlite_pdo_lexer.pl](../../sqlite_pdo_lexer.pl).

## Token Stream

Whitespace and comments are skipped.

$$
\langle tokens \rangle ::= \langle token \rangle^{*}
$$

$$
\langle token \rangle ::=
  \langle string \rangle
  \mid \langle quotedIdentifier \rangle
  \mid \langle placeholder \rangle
  \mid \langle number \rangle
  \mid \langle identifierOrKeyword \rangle
  \mid \langle operator \rangle
  \mid \langle symbol \rangle
$$

## PDO Placeholders

$$
\langle placeholder \rangle ::=
  \texttt{"?"}
  \mid \texttt{"?"}\langle digits \rangle
  \mid \texttt{":"}\langle identifier \rangle
  \mid \texttt{"@"}\langle identifier \rangle
  \mid \texttt{"$"}\langle identifier \rangle
$$

The AST placeholder forms are:

$$
\begin{aligned}
\texttt{"?"} &\mapsto \operatorname{placeholder}(\operatorname{positional}) \\
\texttt{"?42"} &\mapsto \operatorname{placeholder}(\operatorname{indexed}(42)) \\
\texttt{":name"} &\mapsto \operatorname{placeholder}(\operatorname{named}(\texttt{":"}, name))
\end{aligned}
$$

## Literals And Names

$$
\langle string \rangle ::= \texttt{"'"}(\langle char \rangle \mid \texttt{"''"})^{*}\texttt{"'"}
$$

$$
\langle quotedIdentifier \rangle ::=
  \texttt{'"'}\langle char \rangle^{*}\texttt{'"'}
  \mid \texttt{"`"}\langle char \rangle^{*}\texttt{"`"}
  \mid \texttt{"["}\langle char \rangle^{*}\texttt{"]"}
$$

$$
\langle identifier \rangle ::= (\langle alpha \rangle \mid \texttt{"\_"})
  (\langle alnum \rangle \mid \texttt{"\_"} \mid \texttt{"$"})^{*}
$$

$$
\langle number \rangle ::= \langle digits \rangle
  \mid \langle digits \rangle\texttt{"."}\langle digits \rangle
$$

## Operators And Symbols

$$
\langle operator \rangle ::=
  \texttt{"->>"} \mid \texttt{"->"} \mid \texttt{"<="} \mid \texttt{">="}
  \mid \texttt{"<>"} \mid \texttt{"!="} \mid \texttt{"=="}
  \mid \texttt{"||"} \mid \texttt{"<<"} \mid \texttt{">>"}
  \mid \texttt{"="} \mid \texttt{"<"} \mid \texttt{">"}
  \mid \texttt{"+"} \mid \texttt{"-"} \mid \texttt{"*"}
  \mid \texttt{"/"} \mid \texttt{"%"} \mid \texttt{"~"}
  \mid \texttt{"&"} \mid \texttt{"|"}
$$

$$
\langle symbol \rangle ::= \texttt{"("} \mid \texttt{")"} \mid \texttt{","} \mid \texttt{"."} \mid \texttt{";"}
$$
