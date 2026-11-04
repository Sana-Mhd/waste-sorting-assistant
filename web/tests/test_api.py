"""The JSON API, called through Flask's test client."""
from datetime import datetime

import pytest
from web import ScanWorkflow
from web.app import create_app

from conftest import make_services, png_bytes


@pytest.fixture
def client(services):
    return create_app(services).test_client()


def scan_once(services) -> None:
    ScanWorkflow(services).run(png_bytes(), "DO")


def test_regions_lists_dortmund(client):
    response = client.get("/api/regions")
    assert response.status_code == 200
    assert response.get_json() == [{"code": "DO", "name": "Dortmund"}]


def test_rules_gives_one_rule_per_category(client):
    rules = client.get("/api/rules?region=DO").get_json()
    assert sorted(rule["category"] for rule in rules) == ["compostable", "landfill", "recyclable"]
    assert all(rule["region_code"] == "DO" and rule["bin"] and rule["reason"] for rule in rules)


def test_results_is_empty_before_the_first_scan(client):
    assert client.get("/api/results?region=DO").get_json() == []


def test_results_shows_a_stored_scan(client, services):
    scan_once(services)

    record = client.get("/api/results?region=DO").get_json()[0]

    assert record["item"] == "plastic"
    assert record["category"] == "recyclable"
    assert record["confidence"] == 0.9
    assert record["region_code"] == "DO"
    assert record["created_at"].endswith("Z")
    datetime.fromisoformat(record["created_at"])      # a real ISO date


def test_summary_counts_the_scans(client, services):
    scan_once(services)
    scan_once(services)

    summary = client.get("/api/summary?region=DO").get_json()

    assert summary["region_code"] == "DO"
    assert summary["total_scans"] == 2
    assert summary["recycling_rate"] == 100.0
    assert summary["composition"] == {"recyclable": 100.0}
    assert summary["average_confidence"] == 90.0


def test_summary_without_scans_gives_zeros(client):
    summary = client.get("/api/summary").get_json()
    assert summary["total_scans"] == 0
    assert summary["recycling_rate"] == 0.0


def test_default_region_is_used_without_a_region_in_the_address(client):
    assert client.get("/api/summary").get_json()["region_code"] == "DO"


def test_region_code_is_not_case_sensitive(client):
    assert client.get("/api/summary?region=do").status_code == 200


@pytest.mark.parametrize("address", ["rules", "results", "summary"])
def test_unknown_region_gets_a_404_with_a_message(client, address):
    response = client.get(f"/api/{address}?region=XX")
    assert response.status_code == 404
    assert "XX" in response.get_json()["error"]


def test_uncertain_scan_does_not_reach_the_api(tmp_path):
    services = make_services(tmp_path, "glass", 0.3)
    scan_once(services)
    client = create_app(services).test_client()
    assert client.get("/api/results?region=DO").get_json() == []
