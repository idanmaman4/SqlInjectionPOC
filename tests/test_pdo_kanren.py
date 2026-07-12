import html
import re
import sqlite3

import pytest

from pdo_kanren import analyze, injection_possible, legal_injections, pdo_query
from pdo_kanren.analyzer import constraint_from_form
from pdo_kanren.web import app as flask_app, sql_highlight


def rendered_text(markup):
    return html.unescape(re.sub(r"<[^>]+>", "", markup))


def test_quoted_context_confirms_true_false_oracle():
    query = pdo_query("SELECT * FROM users WHERE name = '?' AND active = 1")
    [item] = legal_injections(query, [("controlled", "param")], limit=1)
    assert item["context"] == "string_single"
    assert item["true_response"] == "user found"
    assert item["false_response"] == "user not found"
    assert item["true_payload"] in item["true_final_sql"]
    assert item["false_payload"] in item["false_final_sql"]
    assert "<nested query predicate>" in item["nested_query_template"]
    assert "SELECT active FROM users" in item["nested_query_example"]


def test_numeric_context_confirms_true_false_oracle():
    query = pdo_query("SELECT * FROM users WHERE id = ?")
    constraints = [("controlled", "param"), ("context", "param", "numeric")]
    assert injection_possible(query, constraints)
    [item] = legal_injections(query, constraints, limit=1)
    assert item["context"] == "numeric"
    assert item["true_response"] != item["false_response"]


def test_bound_and_uncontrolled_values_are_not_injectable():
    query = pdo_query("SELECT * FROM users WHERE id = ?")
    assert not injection_possible(query, [("controlled", "param"), ("pdo_bound", "param")])
    assert analyze(query, [("pdo_bound", "param")])["status"] == "safe_by_parameterization"
    assert analyze(query, [])["status"] == "not_attacker_controlled"


def test_constraints_filter_both_probes():
    query = pdo_query("SELECT * FROM users WHERE name = '?'")
    assert legal_injections(query, [("controlled", "param"), ("max_length", "param", 3)]) == []
    assert legal_injections(query, [("controlled", "param"), ("allowed_chars", "param", "' ")]) == []


def test_requires_exactly_one_placeholder():
    constraints = [("controlled", "param")]
    with pytest.raises(ValueError):
        legal_injections(pdo_query("SELECT * FROM users"), constraints)
    with pytest.raises(ValueError):
        legal_injections(pdo_query("SELECT * FROM users WHERE id=? OR c=?"), constraints)


def test_only_read_only_select_templates_are_accepted():
    with pytest.raises(ValueError):
        analyze("DELETE FROM users WHERE id = ?", [("controlled", "param")])


def test_unknown_schema_is_not_reported_as_no_witness():
    result = analyze("SELECT * FROM products WHERE id = ?", [("controlled", "param")])
    assert result["status"] == "unsupported_query_schema"
    assert "no such table" in result["message"]


def test_generated_statements_execute_against_representative_schema():
    items = legal_injections(
        pdo_query("SELECT * FROM accounts WHERE unusual_column = '?'"),
        [("controlled", "param")],
        limit=5,
    )
    assert items
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE accounts (id INTEGER, unusual_column TEXT, c INTEGER)")
    for item in items:
        connection.execute(f"EXPLAIN {item['true_final_sql']}")
        connection.execute(f"EXPLAIN {item['false_final_sql']}")


def test_result_limit_is_stable():
    query = pdo_query("SELECT * FROM users WHERE name = '?'")
    constraints = [("controlled", "param")]
    assert legal_injections(query, constraints, limit=2) == legal_injections(query, constraints, limit=5)[:2]


def test_form_constraint_validation():
    constraints = constraint_from_form(
        controlled=True, context="numeric", max_length="20", allowed_chars="", pdo_bound=False
    )
    assert ("max_length", "param", 20) in constraints
    with pytest.raises(ValueError):
        constraint_from_form(
            controlled=True, context="numeric", max_length="-1", allowed_chars="", pdo_bound=False
        )


def test_sql_highlight_escapes_untrusted_text():
    highlighted = str(sql_highlight("SELECT '<x>' -- tail"))
    assert '<span class="tok-keyword">SELECT</span>' in highlighted
    assert "<x>" not in highlighted


def test_default_page_submission_renders_both_probes():
    with flask_app.test_client() as client:
        response = client.post(
            "/",
            data={
                "sql": "SELECT * FROM users WHERE name = '?' AND active = 1",
                "controlled": "on",
                "limit": "1",
                "max_padding": "4",
                "submit_action": "analyze",
            },
        )
    text = rendered_text(response.get_data(as_text=True))
    assert response.status_code == 200
    assert "confirmed_boolean_oracle" in text
    assert "True payload" in text
    assert "False payload" in text
    assert "Witness 1" in text
    assert "Website response simulation" in text
    assert "user found" in text
    assert "user not found" in text
    assert "Different responses confirm a Boolean oracle" in text
    assert "Where the nested query goes" in text
    assert "&lt;nested query predicate&gt;" in response.get_data(as_text=True)
    assert 'aria-label="Copy true payload for witness 1"' in response.get_data(as_text=True)


def test_default_page_exposes_search_options_and_uses_compact_limit():
    with flask_app.test_client() as client:
        response = client.get("/")
    page = response.get_data(as_text=True)
    assert '<details class="advanced" open>' in page
    assert 'name="limit" value="3"' in page
    assert 'textarea name="sql" rows="5"' in page


@pytest.mark.parametrize("field", ["limit", "max_padding", "payload_index"])
def test_malformed_numeric_form_fields_render_error_instead_of_500(field):
    data = {
        "sql": "SELECT * FROM users WHERE id = ?",
        "controlled": "on",
        "limit": "1",
        "max_padding": "2",
        "payload_index": "0",
        "submit_action": "analyze",
    }
    data[field] = "not-a-number"
    with flask_app.test_client() as client:
        response = client.post("/", data=data)
    assert response.status_code == 200
    assert "Invalid input:" in response.get_data(as_text=True)


def test_generator_steps_and_reports_exhaustion():
    base = {
        "sql": "SELECT * FROM users WHERE name = '?'",
        "controlled": "on",
        "limit": "10",
        "max_padding": "4",
        "payload_index": "0",
    }
    with flask_app.test_client() as client:
        first = client.post("/", data={**base, "submit_action": "generate"})
        second = client.post("/", data={**base, "submit_action": "next"})
    assert "<h2>Payload 1</h2>" in first.get_data(as_text=True)
    assert "Website response simulation" in first.get_data(as_text=True)
    assert "<h2>Payload 2</h2>" in second.get_data(as_text=True)
