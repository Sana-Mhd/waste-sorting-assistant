"""The CoachService: caching, fallback and the shape of the answer."""
import pytest

from coach import (
    CoachConfig,
    CoachService,
    Explanation,
    LanguageModelUnavailable,
    MemoryCache,
    TemplateExplainer,
)
from coach.explainers import BaseExplainer, LanguageModelExplainer


class CountingExplainer(BaseExplainer):
    """Explainer that counts how often it was asked."""

    source = "model"

    def __init__(self, available: bool = True, fail: bool = False) -> None:
        self.calls = 0
        self._available = available
        self._fail = fail

    def is_available(self) -> bool:
        return self._available

    def explain(self, item: str, rule) -> str:
        self.calls += 1
        if self._fail:
            raise LanguageModelUnavailable("pretend the service is down")
        return f"A generated explanation for {item}."


def make_coach(rule_engine, explainer=None) -> CoachService:
    return CoachService(
        rule_engine,
        cache=MemoryCache(),
        explainer=explainer or CountingExplainer(),
        config=CoachConfig(api_key="test-key"),
    )


def test_explain_returns_a_full_explanation(rule_engine):
    coach = make_coach(rule_engine)

    answer = coach.explain("plastic bottle", "recyclable", "DO")

    assert isinstance(answer, Explanation)
    assert answer.text
    assert answer.bin == "Yellow bin (Wertstofftonne)"
    assert answer.category == "recyclable"
    assert answer.region_code == "DO"
    assert answer.source == "model"
    assert answer.from_language_model is True


def test_the_region_code_is_normalised(rule_engine):
    coach = make_coach(rule_engine)
    assert coach.explain("plastic bottle", "recyclable", " do ").region_code == "DO"


def test_an_unknown_category_is_rejected(rule_engine):
    coach = make_coach(rule_engine)
    with pytest.raises(ValueError):
        coach.explain("plastic bottle", "space waste", "DO")


def test_an_empty_item_is_rejected(rule_engine):
    coach = make_coach(rule_engine)
    with pytest.raises(ValueError):
        coach.explain("   ", "recyclable", "DO")


def test_the_second_question_is_answered_from_the_cache(rule_engine):
    explainer = CountingExplainer()
    coach = make_coach(rule_engine, explainer)

    first = coach.explain("plastic bottle", "recyclable", "DO")
    second = coach.explain("plastic bottle", "recyclable", "DO")

    assert explainer.calls == 1, "the language model was asked twice for the same item"
    assert first.text == second.text
    assert second.source == "cache"
    assert len(coach.cache) == 1


def test_a_different_region_is_not_served_from_the_cache(rule_engine):
    explainer = CountingExplainer()
    coach = make_coach(rule_engine, explainer)

    coach.explain("plastic bottle", "recyclable", "DO")
    coach.explain("plastic bottle", "recyclable", "K")

    assert explainer.calls == 2
    assert len(coach.cache) == 2


def test_the_template_is_used_when_the_model_is_not_available(rule_engine):
    coach = make_coach(rule_engine, CountingExplainer(available=False))

    answer = coach.explain("banana peel", "compostable", "DO")

    assert answer.source == "template"
    assert "Biotonne" in answer.bin
    assert answer.text


def test_the_template_is_used_when_the_model_fails(rule_engine):
    explainer = CountingExplainer(fail=True)
    coach = make_coach(rule_engine, explainer)

    answer = coach.explain("ceramic cup", "landfill", "DO")

    assert explainer.calls == 1, "the explainer should have been tried"
    assert answer.source == "template"
    assert answer.text


def test_explain_result_accepts_the_object_of_subsystem_one(rule_engine):
    class FakeResult:
        material = "plastic"
        category = "recyclable"
        confidence = 0.93

    coach = make_coach(rule_engine)
    answer = coach.explain_result(FakeResult(), "DO")

    assert answer.category == "recyclable"
    assert answer.text


# --- the explainers themselves -------------------------------------------------


def test_the_base_explainer_cannot_be_instantiated():
    with pytest.raises(TypeError):
        BaseExplainer()


def test_the_template_explainer_names_the_bin(rule_engine):
    rule = rule_engine.get_rule("recyclable", "DO")
    text = TemplateExplainer().explain("plastic bottle", rule)
    assert "Wertstofftonne" in text
    assert text.startswith("Plastic bottle")


def test_the_template_explainer_can_answer_in_german(rule_engine):
    rule = rule_engine.get_rule("compostable", "DO")
    text = TemplateExplainer("de").explain("bananenschale", rule)
    assert "Biomüll" in text


def test_a_long_answer_is_cut_to_the_promised_length():
    from coach import shorten

    cut = shorten(" ".join(["word"] * 200), 60)
    assert len(cut.split()) == 60


def test_the_template_also_keeps_the_word_limit(rule_engine):
    """The limit is a promise of the subsystem, not only of the language model."""
    rule = rule_engine.get_rule("recyclable", "DO")
    long_rule = type(rule)(
        category=rule.category,
        region_code=rule.region_code,
        bin=rule.bin,
        reason=" ".join(["reason"] * 200),
    )

    text = TemplateExplainer(max_words=60).explain("plastic bottle", long_rule)

    assert len(text.split()) <= 60


def test_the_prompt_contains_the_rule_and_the_limit(rule_engine):
    rule = rule_engine.get_rule("recyclable", "DO")
    explainer = LanguageModelExplainer(config=CoachConfig(api_key="x", max_words=60))

    prompt = explainer.build_prompt("plastic bottle", rule)

    assert "plastic bottle" in prompt
    assert rule.bin in prompt
    assert "60 words" in prompt


def test_a_client_without_a_key_is_not_available():
    explainer = LanguageModelExplainer(config=CoachConfig(api_key=""))
    assert explainer.is_available() is False


def test_sending_without_a_key_raises(rule_engine):
    from coach import OpenAIClient

    client = OpenAIClient(CoachConfig(api_key=""))
    with pytest.raises(LanguageModelUnavailable):
        client.send("anything")
