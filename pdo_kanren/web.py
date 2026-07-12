from __future__ import annotations

import os
import re

from flask import Flask, render_template, request
from markupsafe import Markup, escape

from pdo_kanren import analyze, constraint_from_form, legal_injections, pdo_query


app = Flask(__name__)

SQL_TOKEN_RE = re.compile(
    r"(?P<comment>--[^\n]*)"
    r"|(?P<string>'(?:''|[^'])*')"
    r"|(?P<keyword>\b(?:SELECT|FROM|WHERE|AND|OR|NULL|EXISTS|LIKE|IN|AS|INSERT|UPDATE|DELETE|VALUES|SET)\b)"
    r"|(?P<number>\b\d+(?:\.\d+)?\b)"
    r"|(?P<placeholder>\?)"
    r"|(?P<operator><>|!=|==|<=|>=|=|<|>|\(|\)|,|\*)",
    re.IGNORECASE,
)


@app.template_filter("sql_highlight")
def sql_highlight(value):
    text = str(value)
    pieces = []
    position = 0
    for match in SQL_TOKEN_RE.finditer(text):
        if match.start() > position:
            pieces.append(escape(text[position : match.start()]))
        token = match.group(0)
        kind = match.lastgroup or "text"
        pieces.append(Markup(f'<span class="tok-{kind}">{escape(token)}</span>'))
        position = match.end()
    if position < len(text):
        pieces.append(escape(text[position:]))
    return Markup("").join(pieces)


@app.get("/")
def index():
    default_sql = "SELECT * FROM users WHERE name = '?' AND active = 1"
    return render_index(
        sql=default_sql,
        context="",
        controlled=True,
        pdo_bound=False,
        max_length="",
        allowed_chars="",
        limit=3,
        max_padding=4,
        mode="analyze",
        payload_index=0,
        result=None,
        generator=None,
        error=None,
    )


@app.post("/")
def analyze_query():
    sql = request.form.get("sql", "")
    context = request.form.get("context", "")
    controlled = request.form.get("controlled") == "on"
    pdo_bound = request.form.get("pdo_bound") == "on"
    max_length = request.form.get("max_length", "")
    allowed_chars = request.form.get("allowed_chars", "")
    limit_value = request.form.get("limit", "3") or "3"
    max_padding_value = request.form.get("max_padding", "2") or "2"
    submit_action = request.form.get("submit_action", "analyze")
    payload_index_value = request.form.get("payload_index", "0") or "0"
    mode = "generator" if submit_action in {"generate", "previous", "next"} else "analyze"

    try:
        limit = int(limit_value)
        max_padding = int(max_padding_value)
        payload_index = max(0, int(payload_index_value))
        constraints = constraint_from_form(
            controlled=controlled,
            context=context,
            max_length=max_length,
            allowed_chars=allowed_chars,
            pdo_bound=pdo_bound,
        )
        query = pdo_query(sql)
        if mode == "generator":
            payload_index = next_payload_index(submit_action, payload_index)
            result = None
            generator = generate_payload_at(
                query,
                constraints,
                payload_index=payload_index,
                max_padding=max_padding,
            )
            payload_index = generator["index"]
        else:
            result = analyze(
                query,
                constraints,
                limit=limit,
                max_padding=max_padding,
            )
            generator = None
            payload_index = 0
        error = None
    except (TypeError, ValueError) as exc:
        limit = limit_value
        max_padding = max_padding_value
        payload_index = 0
        result = None
        generator = None
        error = f"Invalid input: {exc}"

    return render_index(
        sql=sql,
        context=context,
        controlled=controlled,
        pdo_bound=pdo_bound,
        max_length=max_length,
        allowed_chars=allowed_chars,
        limit=limit,
        max_padding=max_padding,
        mode=mode,
        payload_index=payload_index,
        result=result,
        generator=generator,
        error=error,
    )


def next_payload_index(submit_action: str, current_index: int) -> int:
    if submit_action == "next":
        return current_index + 1
    if submit_action == "previous":
        return max(0, current_index - 1)
    return 0


def generate_payload_at(query, constraints, *, payload_index: int, max_padding: int):
    requested = legal_injections(
        query,
        constraints,
        limit=payload_index + 1,
        max_padding=max_padding,
    )
    if not requested:
        return {
            "status": "not_possible",
            "payload": None,
            "index": 0,
            "number": 0,
            "has_previous": False,
        }

    if len(requested) <= payload_index:
        payload_index = len(requested) - 1
        status = "exhausted"
    else:
        status = "possible"

    return {
        "status": status,
        "payload": requested[payload_index],
        "index": payload_index,
        "number": payload_index + 1,
        "has_previous": payload_index > 0,
    }


def render_index(**context):
    return render_template("index.html", **context)


def main():
    host = os.environ.get("SQLITE_PDO_ANALYZER_HOST", "127.0.0.1")
    port = int(os.environ.get("SQLITE_PDO_ANALYZER_PORT", "5000"))
    debug = os.environ.get("SQLITE_PDO_ANALYZER_DEBUG", "").lower() in {"1", "true", "yes"}
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
