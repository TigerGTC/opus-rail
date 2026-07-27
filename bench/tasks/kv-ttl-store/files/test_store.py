import time

import store


def test_put_get():
    store.put("a", 1)
    assert store.get("a") == 1


def test_delete():
    store.put("b", 2)
    store.delete("b")
    assert store.get("b") is None


def test_delete_missing_ok():
    store.delete("never-existed")


def test_ttl_expiry():
    store.put_ttl("c", 3, ttl_seconds=0)
    assert store.get("c") is None


def test_ttl_alive():
    store.put_ttl("d", 4, ttl_seconds=60)
    assert store.get("d") == 4


def test_put_clears_old_ttl():
    store.put_ttl("e", 5, ttl_seconds=0)
    store.put("e", 6)
    assert store.get("e") == 6
