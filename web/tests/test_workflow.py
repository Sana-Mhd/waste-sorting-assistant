"""One scan from photo to stored result, against the real subsystems 2 and 3."""
import pytest

from classification import InvalidImageError
from web import ScanWorkflow

from conftest import make_services, png_bytes


def test_confident_scan_is_explained_and_saved(services):
    outcome = ScanWorkflow(services).run(png_bytes(), "DO")

    assert outcome.is_confident
    assert outcome.result.material == "plastic"
    assert outcome.explanation.category == "recyclable"
    assert outcome.explanation.bin
    assert outcome.explanation.text
    assert outcome.was_saved
    assert services.analytics.total_scans("DO") == 1


def test_uncertain_scan_is_not_explained_and_not_saved(tmp_path):
    services = make_services(tmp_path, "glass", 0.3)
    outcome = ScanWorkflow(services).run(png_bytes(), "DO")

    assert not outcome.is_confident
    assert outcome.explanation is None
    assert not outcome.was_saved
    assert services.analytics.total_scans("DO") == 0


@pytest.mark.parametrize("material, category", [("organic", "compostable"), ("trash", "landfill")])
def test_each_category_gets_its_own_bin(tmp_path, material, category):
    outcome = ScanWorkflow(make_services(tmp_path, material, 0.95)).run(png_bytes(), "DO")
    assert outcome.explanation.category == category


def test_invalid_upload_raises_invalid_image_error(services):
    with pytest.raises(InvalidImageError):
        ScanWorkflow(services).run(b"definitely not a photo", "DO")


def test_unknown_region_still_answers_but_is_not_saved(services):
    outcome = ScanWorkflow(services).run(png_bytes(), "XX")

    assert outcome.explanation.bin            # generic rule from subsystem 2
    assert not outcome.was_saved              # the database only accepts known regions
    assert services.analytics.total_scans() == 0


def test_other_region_gets_a_new_explanation_but_no_second_save(services):
    workflow = ScanWorkflow(services)
    first = workflow.run(png_bytes(), "DO")

    moved = workflow.for_region(first, "XX")

    assert moved.explanation.region_code == "XX"
    assert moved.saved_id == first.saved_id
    assert services.analytics.total_scans() == 1


def test_same_region_returns_the_same_outcome(services):
    workflow = ScanWorkflow(services)
    first = workflow.run(png_bytes(), "DO")
    assert workflow.for_region(first, "DO") is first


def test_uncertain_scan_stays_unexplained_in_another_region(tmp_path):
    workflow = ScanWorkflow(make_services(tmp_path, "glass", 0.3))
    first = workflow.run(png_bytes(), "DO")
    assert workflow.for_region(first, "XX") is first


def test_scans_reach_the_dashboard(services):
    workflow = ScanWorkflow(services)
    for _ in range(3):
        workflow.run(png_bytes(), "DO")

    summary = services.analytics.summary("DO")
    assert summary.total_scans == 3
    assert summary.composition == {"recyclable": 100.0}
