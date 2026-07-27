"""Tiny in-memory key-value store."""

_DATA = {}


def put(key, value):
    _DATA[key] = value


def get(key, default=None):
    return _DATA.get(key, default)
