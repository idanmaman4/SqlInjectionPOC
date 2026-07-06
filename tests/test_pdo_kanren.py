from itertools import product
import html
import re
import sqlite3
import unittest

from pdo_kanren import analyze, injection_possible, legal_injections, pdo_query
from pdo_kanren.web import app as flask_app, sql_highlight


STRUCTURAL_TEST_ATOMS = {"'", "''", "--", "OR", "AND", "=", "<>", "EXISTS", "SELECT"}


def sqlite_prepares_with_schema(sql):
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE users (id INTEGER, name TEXT, active INTEGER, c INTEGER)")
    connection.execute("CREATE TABLE accounts (id INTEGER, unusual_column TEXT, c INTEGER)")
    try:
        connection.execute(f"EXPLAIN {sql}")
    except sqlite3.Error:
        return False
    return True


def expected_payloads(sql, tokens, token_count, context):
    before, after = sql.split("?", 1)
    expected = []
    for atoms in product(tokens, repeat=token_count):
        if "--" in atoms[:-1]:
            continue
        if not context_matches(atoms, context):
            continue
        if not any(atom in STRUCTURAL_TEST_ATOMS for atom in atoms[1:]):
            continue
        payload = " ".join(atoms)
        if sqlite_prepares_with_schema(before + payload + after):
            expected.append(payload)
    return expected


def expected_payloads_up_to(sql, tokens, max_token_count, context):
    expected = []
    for token_count in range(1, max_token_count + 1):
        expected.extend(expected_payloads(sql, tokens, token_count, context))
    return expected


def context_matches(atoms, context):
    if context == "string_single":
        return atoms[:1] == ("'",)
    if context == "string_value":
        return atoms[:1] == ("''",)
    if context == "numeric":
        return atoms[:1] in {("1",), ("0",), ("NULL",), ("c",)}
    raise ValueError(f"unknown test context: {context}")


def payloads(items):
    return [item["payload"] for item in items]


def rendered_text(markup):
    return html.unescape(re.sub(r"<[^>]+>", "", markup))


class PdoKanrenTests(unittest.TestCase):
    def test_quoted_placeholder_generates_payload(self):
        query = pdo_query("SELECT * FROM users WHERE name = '?' AND active = 1")
        constraints = [("controlled", "param"), ("allowed_chars", "param", "any")]
        [first] = legal_injections(query, constraints, limit=1, max_padding=2)
        self.assertEqual(first["payload"], "' --")
        self.assertEqual(
            first["final_sql"],
            "SELECT * FROM users WHERE name = '' --' AND active = 1",
        )
        self.assertEqual(first["payload_shape"], "sqlite_valid_token_sequence")

    def test_numeric_context(self):
        query = pdo_query("SELECT * FROM users WHERE id = ?")
        constraints = [("controlled", "param"), ("context", "param", "numeric")]
        self.assertTrue(injection_possible(query, constraints))
        [first] = legal_injections(query, constraints, limit=1, max_padding=2)
        self.assertEqual(first["payload"], "1 --")

    def test_bound_param_blocks_generation(self):
        query = pdo_query("SELECT * FROM users WHERE id = ?")
        constraints = [("controlled", "param"), ("pdo_bound", "param")]
        self.assertFalse(injection_possible(query, constraints))

    def test_max_length_filters(self):
        query = pdo_query("SELECT * FROM users WHERE name = '?'")
        constraints = [("controlled", "param"), ("max_length", "param", 3)]
        self.assertEqual(analyze(query, constraints)["status"], "not_possible")

    def test_requires_one_placeholder(self):
        query = pdo_query("SELECT * FROM users WHERE id = ? AND tenant = ?")
        constraints = [("controlled", "param")]
        with self.assertRaises(ValueError):
            legal_injections(query, constraints, limit=1)

    def test_backtracking_order(self):
        query = pdo_query("SELECT * FROM users WHERE name = '?'")
        constraints = [("controlled", "param")]
        results = legal_injections(query, constraints, limit=3, max_padding=4)
        self.assertEqual(
            [item["payload"] for item in results],
            ["' --", "' OR '", "' AND '"],
        )

    def test_search_depth_is_shortest_first_up_to_limit(self):
        query = pdo_query("SELECT * FROM users WHERE name = '?'")
        constraints = [("controlled", "param")]
        results = legal_injections(query, constraints, limit=10, max_padding=4)
        self.assertTrue(results)
        token_lengths = [len(item["payload"].split()) for item in results]
        self.assertEqual(token_lengths, sorted(token_lengths))
        self.assertEqual(results[0]["payload"], "' --")

    def test_tiny_vocabulary_search_is_exhaustive(self):
        query = pdo_query("SELECT * FROM users WHERE name = '?'")
        constraints = [("controlled", "param"), ("allowed_chars", "param", "'- ")]
        results = legal_injections(query, constraints, limit=10, max_padding=2)
        self.assertEqual([item["payload"] for item in results], ["' --"])

    def test_quoted_context_matches_independent_exhaustive_search(self):
        sql = "SELECT * FROM users WHERE name = '?' AND active = 1"
        tokens = ("'", "''", "--", "OR", "1", "0")
        constraints = [("controlled", "param"), ("allowed_chars", "param", "'-OR10 ")]
        results = legal_injections(pdo_query(sql), constraints, limit=100, max_padding=4)
        self.assertEqual(payloads(results), expected_payloads_up_to(sql, tokens, 4, "string_single"))

    def test_payload_trailing_quote_pairs_with_template_quote(self):
        sql = "SELECT * FROM users WHERE name = '?' AND active = 1"
        constraints = [("controlled", "param")]
        results = legal_injections(pdo_query(sql), constraints, limit=10, max_padding=3)
        payload = "' OR '"
        [item] = [result for result in results if result["payload"] == payload]
        self.assertEqual(
            item["final_sql"],
            "SELECT * FROM users WHERE name = '' OR '' AND active = 1",
        )
        self.assertIn("OR '' AND active", item["final_sql"])
        self.assertTrue(sqlite_prepares_with_schema(item["final_sql"]))

    def test_numeric_context_matches_independent_exhaustive_search(self):
        sql = "SELECT * FROM users WHERE id = ?"
        tokens = ("--", "OR", "1", "0")
        constraints = [
            ("controlled", "param"),
            ("context", "param", "numeric"),
            ("allowed_chars", "param", "-OR10 "),
        ]
        results = legal_injections(pdo_query(sql), constraints, limit=100, max_padding=3)
        self.assertEqual(payloads(results), expected_payloads_up_to(sql, tokens, 3, "numeric"))

    def test_emitted_sql_prepares_against_representative_schema(self):
        query = pdo_query("SELECT * FROM users WHERE name = '?' AND active = 1")
        constraints = [("controlled", "param"), ("allowed_chars", "param", "'-OR10 ")]
        results = legal_injections(query, constraints, limit=100, max_padding=4)
        self.assertTrue(results)
        self.assertTrue(all(sqlite_prepares_with_schema(item["final_sql"]) for item in results))

    def test_limit_truncates_without_changing_order(self):
        query = pdo_query("SELECT * FROM users WHERE name = '?' AND active = 1")
        constraints = [("controlled", "param"), ("allowed_chars", "param", "'-OR10 ")]
        first_three = legal_injections(query, constraints, limit=3, max_padding=4)
        all_results = legal_injections(query, constraints, limit=100, max_padding=4)
        self.assertEqual(payloads(first_three), payloads(all_results)[:3])

    def test_max_length_prunes_exact_depth_when_no_candidate_can_fit(self):
        query = pdo_query("SELECT * FROM users WHERE name = '?'")
        constraints = [("controlled", "param"), ("max_length", "param", 3)]
        self.assertEqual(legal_injections(query, constraints, limit=10, max_padding=4), [])

    def test_allowed_chars_filters_token_vocabulary_before_search(self):
        query = pdo_query("SELECT * FROM users WHERE name = '?'")
        constraints = [("controlled", "param"), ("allowed_chars", "param", "' ")]
        self.assertEqual(legal_injections(query, constraints, limit=10, max_padding=2), [])

    def test_payload_vocabulary_does_not_infer_column_names(self):
        query = pdo_query("SELECT * FROM accounts WHERE unusual_column = '?'")
        constraints = [("controlled", "param")]
        results = legal_injections(query, constraints, limit=5, max_padding=4)
        self.assertTrue(results)
        self.assertFalse(any("unusual_column" in item["payload"] for item in results))
        self.assertTrue(
            all("minimal_fixed_token_vocabulary" in item["evidence"] for item in results)
        )
        self.assertTrue(all("shortest_first_bounded_search" in item["evidence"] for item in results))


class FlaskAppTests(unittest.TestCase):
    def test_sql_highlight_wraps_tokens_and_escapes_plain_text(self):
        highlighted = str(sql_highlight("SELECT '<x>' -- tail"))
        self.assertIn('<span class="tok-keyword">SELECT</span>', highlighted)
        self.assertIn('<span class="tok-string">&#39;&lt;x&gt;&#39;</span>', highlighted)
        self.assertIn('<span class="tok-comment">-- tail</span>', highlighted)
        self.assertNotIn("<x>", highlighted)

    def test_payload_generator_steps_one_payload_at_a_time(self):
        with flask_app.test_client() as client:
            first = client.post(
                "/",
                data={
                    "sql": "SELECT * FROM users WHERE name = '?' AND active = 1",
                    "context": "",
                    "controlled": "on",
                    "max_length": "20",
                    "allowed_chars": "",
                    "limit": "10",
                    "max_padding": "4",
                    "payload_index": "0",
                    "submit_action": "generate",
                },
            )
            self.assertEqual(first.status_code, 200)
            first_html = first.get_data(as_text=True)
            self.assertIn("<h2>Payload 1</h2>", first_html)
            self.assertIn('class="status possible">possible</span>', first_html)
            self.assertIn("' --", rendered_text(first_html))

            second = client.post(
                "/",
                data={
                    "sql": "SELECT * FROM users WHERE name = '?' AND active = 1",
                    "context": "",
                    "controlled": "on",
                    "max_length": "30",
                    "allowed_chars": "",
                    "limit": "10",
                    "max_padding": "4",
                    "payload_index": "0",
                    "submit_action": "next",
                },
            )
            self.assertEqual(second.status_code, 200)
            second_html = second.get_data(as_text=True)
            self.assertIn("<h2>Payload 2</h2>", second_html)
            self.assertIn('class="status possible">possible</span>', second_html)
            self.assertIn("' OR '", rendered_text(second_html))

    def test_payload_generator_reports_exhaustion(self):
        with flask_app.test_client() as client:
            response = client.post(
                "/",
                data={
                    "sql": "SELECT * FROM users WHERE name = '?'",
                    "context": "",
                    "controlled": "on",
                    "max_length": "",
                    "allowed_chars": "'- ",
                    "limit": "10",
                    "max_padding": "2",
                    "payload_index": "0",
                    "submit_action": "next",
                },
            )
            self.assertEqual(response.status_code, 200)
            html = response.get_data(as_text=True)
            self.assertIn("<h2>Payload 1</h2>", html)
            self.assertIn('class="status exhausted">exhausted</span>', html)
            self.assertIn("No later payload is available", html)


if __name__ == "__main__":
    unittest.main()
