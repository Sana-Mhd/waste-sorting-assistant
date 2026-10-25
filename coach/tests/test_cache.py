"""The explanation cache: keys, both implementations, and failure behaviour."""
import pytest

from coach import MemoryCache, SQLiteCache, make_key
from coach.cache import BaseCache


def test_the_base_cache_cannot_be_instantiated():
    with pytest.raises(TypeError):
        BaseCache()


def test_the_key_ignores_case_and_spaces():
    assert make_key(" Plastic Bottle ", "Recyclable", "do") == make_key(
        "plastic bottle", "recyclable", "DO"
    )


def test_different_regions_get_different_keys():
    assert make_key("plastic bottle", "recyclable", "DO") != make_key(
        "plastic bottle", "recyclable", "K"
    )


def test_different_languages_get_different_keys():
    assert make_key("plastic bottle", "recyclable", "DO", "en") != make_key(
        "plastic bottle", "recyclable", "DO", "de"
    )


@pytest.mark.parametrize("cache_name", ["memory", "sqlite"])
def test_both_caches_store_and_return_a_text(cache_name, tmp_path):
    cache = MemoryCache() if cache_name == "memory" else SQLiteCache(tmp_path / "c.db")

    key = make_key("plastic bottle", "recyclable", "DO")
    assert cache.get(key) is None
    assert len(cache) == 0

    cache.set(key, "Put it in the yellow bin.")
    assert cache.get(key) == "Put it in the yellow bin."
    assert len(cache) == 1


@pytest.mark.parametrize("cache_name", ["memory", "sqlite"])
def test_storing_the_same_key_twice_keeps_one_entry(cache_name, tmp_path):
    cache = MemoryCache() if cache_name == "memory" else SQLiteCache(tmp_path / "c.db")
    key = make_key("plastic bottle", "recyclable", "DO")

    cache.set(key, "first")
    cache.set(key, "second")

    assert len(cache) == 1
    assert cache.get(key) == "second"


def test_the_sqlite_cache_survives_a_restart(tmp_path):
    path = tmp_path / "cache.db"
    key = make_key("banana peel", "compostable", "DO")

    SQLiteCache(path).set(key, "Brown bin, no plastic bag.")

    reopened = SQLiteCache(path)
    assert reopened.get(key) == "Brown bin, no plastic bag."


def test_clearing_empties_the_cache(tmp_path):
    cache = SQLiteCache(tmp_path / "c.db")
    cache.set(make_key("a", "landfill", "DO"), "text")
    cache.clear()
    assert len(cache) == 0
