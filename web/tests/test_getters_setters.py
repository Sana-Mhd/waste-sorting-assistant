"""Getters and setters of the web classes (Hometask 1)."""
import pytest

from web import ScanWorkflow
from web.pages import AboutPage
from web.scan_store import ScanStore


def test_page_services(services):
    page = AboutPage(services)
    assert page.services is services

    other = object()
    page.services = other
    assert page.services is other


def test_workflow_services(services):
    workflow = ScanWorkflow(services)
    assert workflow.services is services

    other = object()
    workflow.services = other
    assert workflow.services is other


def test_scan_store_max_scans():
    store = ScanStore(max_scans=5)
    assert store.max_scans == 5

    store.max_scans = 2
    assert store.max_scans == 2

    with pytest.raises(ValueError):
        store.max_scans = 0
