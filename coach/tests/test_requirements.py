"""One test per requirement of subsystem 3.

Every test here carries the number of the requirement it proves, so the list in
`docs/REQUIREMENTS.md` can be checked against a test run instead of being
believed. The other test files cover the same behaviour in more detail; this
file is the traceability matrix.

Run only these with:

    python -m pytest tests/test_requirements.py -v
"""
from __future__ import annotations

import inspect
import time
from pathlib import Path

import pytest

import coach as coach_package
from coach import (
    AnalyticsService,
    CoachConfig,
    CoachService,
    Explanation,
    LanguageModelExplainer,
    MemoryCache,
    Summary,
    TemplateExplainer,
    charts,
    shorten,
)
from coach.explainers import BaseExplainer

SOURCE_DIR = Path(__file__).resolve().parents[1] / "src" / "coach"


class FakeExplainer(BaseExplainer):
    """A stand-in language model: no network, and it counts its calls."""

    source = "model"

    def __init__(self, available: bool = True) -> None:
        self.calls = 0
        self._available = available

    def is_available(self) -> bool:
        return self._available

    def explain(self, item: str, rule) -> str:
        self.calls += 1
        return f"A generated explanation for {item}."


def make_coach(rule_engine, explainer=None, **config_kwargs) -> CoachService:
    return CoachService(
        rule_engine,
        cache=MemoryCache(),
        explainer=explainer or FakeExplainer(),
        config=CoachConfig(api_key="test-key", **config_kwargs),
    )


# =============================================================================
# Functional requirements
# =============================================================================


@pytest.mark.requirement("F1")
def test_f1_an_explanation_is_generated_for_a_classified_item(rule_engine):
    """F1: produce an explanation for one classified item."""
    answer = make_coach(rule_engine).explain("plastic bottle", "recyclable", "DO")
    assert isinstance(answer, Explanation)
    assert answer.text.strip()


@pytest.mark.requirement("F2")
def test_f2_the_rule_of_the_users_region_is_applied(rule_engine):
    """F2: the answer follows the rule of the region the user chose."""
    coach = make_coach(rule_engine)

    coach.explain("plastic bottle", "recyclable", "DO")
    coach.explain("plastic bottle", "recyclable", "K")

    assert ("recyclable", "DO") in rule_engine.calls
    assert ("recyclable", "K") in rule_engine.calls


@pytest.mark.requirement("F3")
def test_f3_the_result_is_a_structured_object(rule_engine):
    """F3: the answer is a typed object, not a loose string."""
    answer = make_coach(rule_engine).explain("banana peel", "compostable", "DO")

    assert answer.text and answer.bin
    assert answer.category == "compostable"
    assert answer.region_code == "DO"
    assert answer.source in {"model", "cache", "template"}


@pytest.mark.requirement("F4")
def test_f4_the_same_question_is_answered_from_the_cache(rule_engine):
    """F4: an item already explained is never sent to the model twice."""
    explainer = FakeExplainer()
    coach = make_coach(rule_engine, explainer)

    first = coach.explain("plastic bottle", "recyclable", "DO")
    second = coach.explain("plastic bottle", "recyclable", "DO")

    assert explainer.calls == 1
    assert second.source == "cache"
    assert first.text == second.text


@pytest.mark.requirement("F5")
def test_f5_a_stored_text_is_served_when_the_model_is_unavailable(rule_engine):
    """F5: no key, no network - the user still gets a correct answer."""
    coach = make_coach(rule_engine, FakeExplainer(available=False))

    answer = coach.explain("ceramic cup", "landfill", "DO")

    assert answer.source == "template"
    assert answer.bin in answer.text


@pytest.mark.requirement("F6")
def test_f6_scans_are_aggregated_into_a_waste_composition(dal):
    """F6: the stored scans become a share per category."""
    shares = AnalyticsService(dal).composition("DO")

    assert shares == {"recyclable": 55.6, "compostable": 22.2, "landfill": 22.2}


@pytest.mark.requirement("F7")
def test_f7_the_recycling_rate_is_computed_per_region(dal):
    """F7: seven of nine scans avoided the residual waste bin."""
    analytics = AnalyticsService(dal)

    assert analytics.recycling_rate("DO") == 77.8
    assert analytics.recycling_rate("K") == 0.0


@pytest.mark.requirement("F8")
def test_f8_the_trend_over_a_period_is_computed(dal):
    """F8: scans per day over a window the caller chooses."""
    trend = AnalyticsService(dal).trend("DO", days=5)

    assert len(trend) == 5
    assert trend["scans"].sum() == 9
    assert list(trend.columns) == ["date", "scans", "recycled"]


@pytest.mark.requirement("F9")
def test_f9_the_dashboard_charts_are_rendered(dal):
    """F9: every figure of the dashboard is produced by this subsystem."""
    analytics = AnalyticsService(dal)

    for figure in (
        charts.composition_chart(analytics, "DO"),
        charts.trend_chart(analytics, "DO"),
        charts.top_items_chart(analytics, "DO"),
    ):
        assert figure.data, "the figure carries no data"


@pytest.mark.requirement("F10")
def test_f10_the_public_interface_is_offered_to_the_other_subsystems():
    """F10: the names the other subsystems import are part of the package."""
    for name in (
        "create_coach_services",
        "CoachService",
        "AnalyticsService",
        "Explanation",
        "Summary",
        "charts",
    ):
        assert name in coach_package.__all__
        assert hasattr(coach_package, name)


@pytest.mark.requirement("F10")
def test_f10_one_call_builds_both_services(dal, rule_engine):
    """F10: subsystem 4 needs a single entry point, not a construction manual."""
    coach, analytics = coach_package.create_coach_services(dal, rule_engine)

    assert isinstance(coach, CoachService)
    assert isinstance(analytics, AnalyticsService)
    assert isinstance(analytics.summary("DO"), Summary)


# =============================================================================
# Non-functional requirements
# =============================================================================


@pytest.mark.requirement("N1")
def test_n1_an_explanation_is_returned_within_three_seconds(rule_engine):
    """N1: the answer the user waits for is produced in under three seconds."""
    coach = make_coach(rule_engine, FakeExplainer(available=False))

    started = time.perf_counter()
    coach.explain("plastic bottle", "recyclable", "DO")
    elapsed = time.perf_counter() - started

    assert elapsed < 3.0


@pytest.mark.requirement("N1")
def test_n1_the_wait_for_the_model_is_bounded(rule_engine):
    """N1: the timeout is configured, so a slow service cannot block the app."""
    coach = make_coach(rule_engine, timeout=3.0)
    assert coach.config.timeout <= 3.0


@pytest.mark.requirement("N2")
def test_n2_a_cached_answer_is_returned_within_200_milliseconds(rule_engine):
    """N2: the second answer comes from the cache and is fast."""
    coach = make_coach(rule_engine)
    coach.explain("plastic bottle", "recyclable", "DO")

    started = time.perf_counter()
    answer = coach.explain("plastic bottle", "recyclable", "DO")
    elapsed = time.perf_counter() - started

    assert answer.source == "cache"
    assert elapsed < 0.2


@pytest.mark.requirement("N3")
def test_n3_the_key_is_read_from_the_environment(monkeypatch):
    """N3: the key comes from the environment, not from a constant."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-from-the-environment")
    assert CoachConfig.from_env().api_key == "sk-from-the-environment"

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert CoachConfig.from_env().api_key == ""


@pytest.mark.requirement("N3")
def test_n3_no_key_is_written_into_the_source_code():
    """N3: nothing that looks like a key may be committed."""
    for path in SOURCE_DIR.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "sk-" not in text, f"{path.name} contains something that looks like a key"


@pytest.mark.requirement("N3")
def test_n3_the_key_never_appears_in_a_log_line_or_traceback():
    """N3: printing the configuration must not reveal the key."""
    config = CoachConfig(api_key="sk-super-secret-value")
    assert "super-secret" not in repr(config)
    assert "super-secret" not in repr(coach_package.OpenAIClient(config))


@pytest.mark.requirement("N4")
def test_n4_no_personal_data_is_sent_to_the_external_service(rule_engine):
    """N4: the prompt holds the item, the rule and the region - nothing else."""
    rule = rule_engine.get_rule("recyclable", "DO")
    explainer = LanguageModelExplainer(config=CoachConfig(api_key="x"))

    prompt = explainer.build_prompt("plastic bottle", rule)

    for forbidden in ("user", "e-mail", "email", "@", "password", "address", "name of the"):
        assert forbidden not in prompt.lower(), f"the prompt mentions {forbidden!r}"


@pytest.mark.requirement("N4")
def test_n4_the_photo_itself_never_leaves_the_system(rule_engine):
    """N4: the coach is given a word, never an image."""
    signature = inspect.signature(CoachService.explain)
    assert list(signature.parameters) == ["self", "item", "category", "region_code"]


@pytest.mark.requirement("N5")
def test_n5_an_explanation_is_never_longer_than_sixty_words(rule_engine):
    """N5: the promised reading length holds for every source of the text."""
    rule = rule_engine.get_rule("recyclable", "DO")
    long_rule = type(rule)(
        category=rule.category,
        region_code=rule.region_code,
        bin=rule.bin,
        reason=" ".join(["reason"] * 300),
    )

    from_template = TemplateExplainer(max_words=60).explain("plastic bottle", long_rule)
    from_model = shorten(" ".join(["word"] * 300), 60)

    assert len(from_template.split()) <= 60
    assert len(from_model.split()) <= 60


@pytest.mark.requirement("N6")
def test_n6_the_chart_colours_are_distinguishable_and_fixed():
    """N6: one colour per category, never cycled, never reused."""
    colours = charts.CATEGORY_COLORS
    assert set(colours) == set(charts.CATEGORY_ORDER)
    assert len(set(colours.values())) == len(colours)


@pytest.mark.requirement("N6")
def test_n6_colour_is_never_the_only_encoding(dal):
    """N6: a reader who cannot separate the hues still reads the chart."""
    analytics = AnalyticsService(dal)

    figure = charts.composition_chart(analytics, "DO")
    assert figure.data[0].text, "the bars carry no value labels"

    table = charts.composition_table(analytics, "DO")
    assert not table.empty, "there is no table view of the same numbers"


@pytest.mark.requirement("N7")
def test_n7_the_tests_need_no_network_connection(rule_engine):
    """N7: the suite runs offline, so it costs nothing and never flakes."""
    coach = CoachService(
        rule_engine, cache=MemoryCache(), config=CoachConfig(api_key="")
    )
    answer = coach.explain("plastic bottle", "recyclable", "DO")

    assert answer.source == "template"


@pytest.mark.requirement("N8")
def test_n8_the_application_stays_usable_when_the_service_fails(rule_engine):
    """N8: an error inside the explainer must not reach the user."""
    from coach import LanguageModelUnavailable

    class BrokenExplainer(BaseExplainer):
        source = "model"

        def is_available(self) -> bool:
            return True

        def explain(self, item: str, rule) -> str:
            raise LanguageModelUnavailable("pretend the service is down")

    coach = make_coach(rule_engine, BrokenExplainer())
    answer = coach.explain("glass jar", "recyclable", "DO")

    assert answer.source == "template"
    assert answer.text


@pytest.mark.requirement("N9")
def test_n9_explanations_are_available_in_german_and_english(rule_engine):
    """N9: the resident reads the answer in a language they speak."""
    rule = rule_engine.get_rule("compostable", "DO")

    english = TemplateExplainer("en").explain("banana peel", rule)
    german = TemplateExplainer("de").explain("bananenschale", rule)

    assert "organic waste" in english
    assert "Biomüll" in german

    prompt = LanguageModelExplainer(
        config=CoachConfig(api_key="x", language="de")
    ).build_prompt("bananenschale", rule)
    assert "German" in prompt


@pytest.mark.requirement("N10")
def test_n10_another_provider_can_replace_the_language_model(rule_engine):
    """N10: a new explainer is plugged in without touching any other module."""

    class OtherProvider(BaseExplainer):
        source = "model"

        def explain(self, item: str, rule) -> str:
            return f"Answer about {item} from a completely different provider."

    coach = make_coach(rule_engine, OtherProvider())
    answer = coach.explain("metal can", "recyclable", "DO")

    assert "different provider" in answer.text
    assert answer.source == "model"


@pytest.mark.requirement("N10")
def test_n10_the_cache_can_be_replaced_the_same_way(rule_engine, tmp_path):
    """N10: the same freedom applies to where the answers are stored."""
    from coach import SQLiteCache

    coach = CoachService(
        rule_engine,
        cache=SQLiteCache(tmp_path / "other.db"),
        explainer=FakeExplainer(),
        config=CoachConfig(api_key="test-key"),
    )
    coach.explain("plastic bottle", "recyclable", "DO")

    assert len(coach.cache) == 1
    assert (tmp_path / "other.db").exists()
