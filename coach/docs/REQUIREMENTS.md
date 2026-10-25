# Requirements — Subsystem 3: AI Coach & Analytics

Ten functional and ten non-functional requirements. Every one of them is proved
by a test in `tests/test_requirements.py`, so this list can be checked against a
test run instead of being believed:

```bash
python -m pytest tests/test_requirements.py -v
```

## Functional requirements

What the subsystem must do.

| # | Requirement | Proved by |
|---|---|---|
| **F1** | Produce a short explanation for an item that subsystem 1 has classified. | `test_f1_an_explanation_is_generated_for_a_classified_item` |
| **F2** | Apply the recycling rule of the region the user selected, by asking subsystem 2 for it. | `test_f2_the_rule_of_the_users_region_is_applied` |
| **F3** | Return the answer as a structured object (`Explanation`) with the text, the bin, the category, the region and where the text came from. | `test_f3_the_result_is_a_structured_object` |
| **F4** | Store every finished explanation, so the same item in the same region is never sent to the language model twice. | `test_f4_the_same_question_is_answered_from_the_cache` |
| **F5** | Serve an explanation built from the local rule when the language model is unavailable. | `test_f5_a_stored_text_is_served_when_the_model_is_unavailable` |
| **F6** | Aggregate the stored classifications into the waste composition of a region. | `test_f6_scans_are_aggregated_into_a_waste_composition` |
| **F7** | Compute the recycling rate of a region, counting recyclable and compostable waste. | `test_f7_the_recycling_rate_is_computed_per_region` |
| **F8** | Compute the number of scans per day over a period the caller chooses, with days without scans counted as zero. | `test_f8_the_trend_over_a_period_is_computed` |
| **F9** | Render the figures of the municipality dashboard: composition, trend and most scanned items. | `test_f9_the_dashboard_charts_are_rendered` |
| **F10** | Offer the coach and the analytics to the other subsystems behind one documented interface. | `test_f10_the_public_interface_is_offered_to_the_other_subsystems`, `test_f10_one_call_builds_both_services` |

## Non-functional requirements

How well it must do it.

| # | Requirement | Proved by |
|---|---|---|
| **N1** | An explanation reaches the user within 3 seconds; the wait for the language model is bounded by a timeout. | `test_n1_an_explanation_is_returned_within_three_seconds`, `test_n1_the_wait_for_the_model_is_bounded` |
| **N2** | An explanation already stored is returned within 200 ms. | `test_n2_a_cached_answer_is_returned_within_200_milliseconds` |
| **N3** | The API key is read from the environment, never written into the code, and never printed in a log line or a traceback. | `test_n3_the_key_is_read_from_the_environment`, `test_n3_no_key_is_written_into_the_source_code`, `test_n3_the_key_never_appears_in_a_log_line_or_traceback` |
| **N4** | No personal data and no photo leave the system: the prompt contains the item, the rule and the region code only. | `test_n4_no_personal_data_is_sent_to_the_external_service`, `test_n4_the_photo_itself_never_leaves_the_system` |
| **N5** | An explanation is at most 60 words, whichever source produced it. | `test_n5_an_explanation_is_never_longer_than_sixty_words` |
| **N6** | Each waste category keeps one fixed colour on every chart, the three colours stay apart for colour-vision deficiency, and colour is never the only encoding. | `test_n6_the_chart_colours_are_distinguishable_and_fixed`, `test_n6_colour_is_never_the_only_encoding` |
| **N7** | The test suite runs without a network connection and without an API key, so it costs nothing and never flakes. | `test_n7_the_tests_need_no_network_connection` |
| **N8** | An error inside the language model never reaches the user: the application keeps working. | `test_n8_the_application_stays_usable_when_the_service_fails` |
| **N9** | Explanations are available in English and German. | `test_n9_explanations_are_available_in_german_and_english` |
| **N10** | The language model and the storage of the cache can each be replaced without changing any other module. | `test_n10_another_provider_can_replace_the_language_model`, `test_n10_the_cache_can_be_replaced_the_same_way` |

## How the requirements are met

**F1–F5, the coach.** `CoachService.explain` asks subsystem 2 for the rule,
builds a key from item, category, region and language, and looks in the cache.
On a miss it asks the preferred explainer and stores the answer. If the
explainer has no key, times out or errors, the `TemplateExplainer` builds the
text from the rule alone. The user therefore always gets an answer (F5, N8),
and never pays twice for the same one (F4, N2).

**F6–F9, the analytics.** `AnalyticsService` reads the stored classifications
through subsystem 2's data access layer, turns them into a pandas DataFrame
once, and computes every figure from that one table. `charts` builds the three
plotly figures the dashboard shows.

**F10, the interface.** `create_coach_services(dal, rule_engine)` returns both
services ready to use, so subsystem 4 writes two lines instead of assembling
five objects.

**N3, N4, the secrets and the privacy.** The key lives in `OPENAI_API_KEY` and
is masked by `CoachConfig.__repr__`. The prompt is built in one place,
`LanguageModelExplainer.build_prompt`, and contains nothing but the item, the
bin, the official reason and the region code. The photo never reaches this
subsystem at all: `explain` takes a word.

**N6, the charts.** The three category colours were checked with a
colour-vision simulation: no two of them are confusable for protan, deutan or
tritan vision, and each has at least 3:1 contrast against the chart surface.
Every bar also carries its value as text, and `charts.composition_table`
returns the same numbers as a table.

**N10, the replaceability.** `BaseExplainer` and `BaseCache` are abstract
classes. `CoachService` only ever calls their methods, so a different provider
or a different store is one constructor argument away.
