from datetime import datetime, timedelta, timezone

import pytest


def test_save_and_get_result(dal):
    rid = dal.save_result("Plastic Bottle", "recyclable", 0.93, "do")
    results = dal.get_results()
    assert len(results) == 1
    r = results[0]
    assert r.id == rid
    assert r.item == "plastic bottle"          # normalised
    assert r.category == "recyclable"
    assert r.confidence == pytest.approx(0.93)
    assert r.region_code == "DO"


def test_same_item_is_stored_once(dal):
    dal.save_result("banana peel", "compostable", 0.9, "DO")
    dal.save_result("Banana Peel", "compostable", 0.8, "DO")
    assert len(dal.get_results()) == 2


def test_filter_by_region(dal):
    dal.add_region("KO", "Koeln")
    dal.save_result("glass jar", "recyclable", 0.9, "DO")
    dal.save_result("glass jar", "recyclable", 0.9, "KO")
    assert len(dal.get_results(region_code="DO")) == 1
    assert len(dal.get_results(region_code="KO")) == 1
    assert len(dal.get_results()) == 2


def test_filter_by_time_period(dal):
    dal.save_result("can", "recyclable", 0.9, "DO")
    now = datetime.now(timezone.utc)
    assert len(dal.get_results(since=now - timedelta(minutes=1))) == 1
    assert len(dal.get_results(since=now + timedelta(minutes=1))) == 0
    assert len(dal.get_results(until=now - timedelta(minutes=1))) == 0


def test_user_is_created_once(dal):
    assert dal.get_or_create_user("lena") == dal.get_or_create_user("lena")


@pytest.mark.parametrize("confidence", [-0.1, 1.5])
def test_confidence_out_of_range_is_rejected(dal, confidence):
    with pytest.raises(ValueError):
        dal.save_result("can", "recyclable", confidence, "DO")


def test_unknown_category_is_rejected(dal):
    with pytest.raises(ValueError):
        dal.save_result("can", "metal", 0.9, "DO")


def test_unknown_region_is_rejected(dal):
    with pytest.raises(ValueError):
        dal.save_result("can", "recyclable", 0.9, "XX")


def test_empty_item_is_rejected(dal):
    with pytest.raises(ValueError):
        dal.save_result("   ", "recyclable", 0.9, "DO")


def test_new_region_needs_no_code_change(dal):
    dal.add_region("KO", "Koeln")
    dal.set_rule("KO", "landfill", "Black bin", "Residual waste.")
    assert dal.get_rule("landfill", "KO").bin == "Black bin"
    assert "KO" in [code for code, _ in dal.list_regions()]


def test_set_rule_updates_existing_rule(dal):
    dal.set_rule("DO", "landfill", "New grey bin", "Updated.")
    assert dal.get_rule("landfill", "DO").bin == "New grey bin"
    assert len(dal.get_rules("DO")) == 3


def test_region_and_rule_need_valid_input(dal):
    with pytest.raises(ValueError):
        dal.add_region("  ", "Nowhere")
    with pytest.raises(ValueError):
        dal.set_rule("XX", "landfill", "bin", "reason")     # region does not exist
    with pytest.raises(ValueError):
        dal.set_rule("DO", "metal", "bin", "reason")        # category does not exist


def test_database_refuses_a_rule_for_a_missing_region(dal):
    """Foreign keys are really switched on (non-functional requirement 3)."""
    from sqlalchemy.exc import IntegrityError

    from data_rules.models import RuleRow

    with dal._sf() as s:
        s.add(RuleRow(region_code="ZZ", category="landfill", bin="b", reason="r"))
        with pytest.raises(IntegrityError):
            s.commit()


def test_database_refuses_a_second_rule_for_the_same_pair(dal):
    from sqlalchemy.exc import IntegrityError

    from data_rules.models import RuleRow

    with dal._sf() as s:
        s.add(RuleRow(region_code="DO", category="landfill", bin="b", reason="r"))
        with pytest.raises(IntegrityError):
            s.commit()


def test_database_refuses_confidence_out_of_range(dal):
    from sqlalchemy.exc import IntegrityError

    from data_rules.models import ClassificationResultRow, Item

    with dal._sf() as s:
        item = Item(name="x")
        s.add(item)
        s.flush()
        s.add(ClassificationResultRow(item_id=item.id, region_code="DO", category="landfill", confidence=2.0))
        with pytest.raises(IntegrityError):
            s.commit()
