"""Minimal INI-style config parser.

Format: [section] headers, key = value pairs, # comments, blank lines ignored.
Values: ints when they look like ints (including negatives), else strings with
surrounding whitespace stripped.
"""


def _coerce(value):
    if value.isdigit():
        return int(value)
    return value


def parse(text):
    result = {}
    section = "default"
    for raw in text.splitlines():
        line = raw.lstrip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:]
            result.setdefault(section, {})
            continue
        if "=" not in line:
            continue
        key, value = line.split("=")
        result.setdefault(section, {})[key.strip()] = _coerce(value)
    return result
