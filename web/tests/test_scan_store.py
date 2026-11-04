"""The memory of the latest scans."""
import pytest

from web import ScanWorkflow
from web.scan_store import ScanStore

from conftest import png_bytes


@pytest.fixture
def outcome(services):
    return ScanWorkflow(services).run(png_bytes(), "DO")


def test_a_stored_scan_can_be_read_again(outcome):
    store = ScanStore()
    scan_id = store.add(outcome, b"photo")

    stored = store.get(scan_id)

    assert stored.outcome is outcome
    assert stored.photo == b"photo"


def test_every_scan_gets_its_own_id(outcome):
    store = ScanStore()
    assert store.add(outcome, b"a") != store.add(outcome, b"a")


@pytest.mark.parametrize("scan_id", [None, "", "unknown"])
def test_unknown_id_gives_none(scan_id):
    assert ScanStore().get(scan_id) is None


def test_the_oldest_scan_is_dropped_when_the_store_is_full(outcome):
    store = ScanStore(max_scans=2)
    oldest = store.add(outcome, b"1")
    middle = store.add(outcome, b"2")
    newest = store.add(outcome, b"3")

    assert store.get(oldest) is None
    assert store.get(middle) is not None
    assert store.get(newest) is not None


def test_a_store_must_have_room_for_a_scan():
    with pytest.raises(ValueError):
        ScanStore(max_scans=0)
