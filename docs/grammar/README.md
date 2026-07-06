# SQLite PDO Grammar Notes

These files describe the supported grammar using Markdown with LaTeX-style
production rules. They document the grammar implemented by the Prolog modules,
not the complete SQLite grammar.

## Notation

Terminals are written as quoted SQL text:

$$
\texttt{"SELECT"}
$$

Lexer token classes are written in angle brackets:

$$
\langle identifier \rangle,\quad
\langle string \rangle,\quad
\langle placeholder \rangle
$$

Optional rules use:

$$
[X]
$$

Repetition uses:

$$
X^{*}
$$

One-or-more comma-separated lists use:

$$
X (\,\texttt{","}\ X\,)^{*}
$$

## Files

- [tokens.md](tokens.md): lexer tokens and PDO placeholders.
- [statements.md](statements.md): top-level statement dispatch and `WITH`.
- [select.md](select.md): `SELECT` grammar.
- [insert.md](insert.md): `INSERT` grammar.
- [update.md](update.md): `UPDATE` grammar.
- [delete.md](delete.md): `DELETE` grammar.
- [expressions.md](expressions.md): expression grammar.
