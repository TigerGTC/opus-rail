"""Log triage helpers. Log lines look like: "LEVEL some message text"."""


def parse_line(line):
    parts = line.strip().split(" ", 1)
    if len(parts) != 2 or not parts[0].isupper():
        return None
    return parts[0], parts[1]


def count_by_level(lines):
    """Return {level: count}, ignoring unparseable lines."""
    raise NotImplementedError  # TODO


def worst_offenders(lines, level, top_n=3):
    """Return the top_n most frequent messages at `level`, most frequent first;
    ties broken alphabetically."""
    raise NotImplementedError  # TODO
