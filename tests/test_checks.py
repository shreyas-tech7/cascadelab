from cascadelab.checks import parse_json, parse_number, run_tests, schema_ok, strip_fence


def test_parse_number():
    assert parse_number("42") == 42.0
    assert parse_number(" $1,250 ") == 1250.0
    assert parse_number("```\n-3.5\n```") == -3.5
    assert parse_number("I need more information to answer this.") is None
    assert parse_number("The answer is 4") is None


def test_parse_json_and_schema():
    schema = {"a": "integer", "b": "string", "c": "boolean", "d": "number", "e": "array"}
    good = '```json\n{"a": 1, "b": "x", "c": true, "d": 2, "e": []}\n```'
    assert schema_ok(parse_json(good), schema)
    assert not schema_ok(parse_json('{"a": true, "b": "x", "c": true, "d": 2, "e": []}'), schema)
    assert not schema_ok(parse_json('{"a": 1, "b": "x", "c": true, "d": 2}'), schema)
    assert parse_json('Here: {"a": 1') is None
    assert parse_json("[1, 2]") is None


def test_run_tests_pass_fail_and_timeout():
    """Broken cases: a failing assert, a syntax error and an endless loop all count as fail."""
    code = "def f(x):\n    return x + 1\n"
    assert run_tests(code, ("assert f(1) == 2",))
    assert not run_tests(code, ("assert f(1) == 3",))
    assert not run_tests("def f(:\n", ("assert f(1) == 2",))
    assert not run_tests("while True:\n    pass\n", ())


def test_strip_fence():
    assert strip_fence("```python\nx = 1\n```") == "x = 1"
    assert strip_fence("x = 1") == "x = 1"
