import confparse

SAMPLE = """
# comment
top = 1

[server]
host = example.com
port = 8080
retries = -3
motto = a = b = c
"""


def test_sections_named_without_brackets():
    parsed = confparse.parse(SAMPLE)
    assert "server" in parsed
    assert "[server]" not in parsed


def test_default_section():
    assert confparse.parse(SAMPLE)["default"]["top"] == 1


def test_string_values_stripped():
    assert confparse.parse(SAMPLE)["server"]["host"] == "example.com"


def test_int_coercion():
    assert confparse.parse(SAMPLE)["server"]["port"] == 8080


def test_negative_int_coercion():
    assert confparse.parse(SAMPLE)["server"]["retries"] == -3


def test_value_may_contain_equals():
    assert confparse.parse(SAMPLE)["server"]["motto"] == "a = b = c"
