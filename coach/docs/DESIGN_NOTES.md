# Design notes — Subsystem 3

Short answers to the questions that come up when reading the code or watching
the presentation.

## Which object-oriented concepts are used, and where

| Concept | Where | Why it is there, not decoration |
|---|---|---|
| **Abstract class** | `BaseCache`, `BaseExplainer` | both have two implementations that must be interchangeable; the abstract class is the contract between them and `CoachService` |
| **Inheritance** | `MemoryCache`/`SQLiteCache` from `BaseCache`; `TemplateExplainer`/`LanguageModelExplainer` from `BaseExplainer` | the shared part (the interface, the word limit) is written once |
| **Polymorphism** | `CoachService._generate` calls `self.explainer.explain(...)` | the same line produces a model answer or a template answer depending on the object behind the interface; there is no `if` about which one is in use |
| **Composition** | `CoachService` owns its cache and its fallback explainer | they are created with it, they live and die with it, nobody else holds them |
| **Aggregation** | `CoachService` holds a `RuleEngine`, `AnalyticsService` holds a `DataAccessLayer` | both are handed in from outside and belong to subsystem 2; this subsystem uses them but does not own them |
| **Encapsulation** | `CoachConfig.api_key` is masked in `__repr__`; `OpenAIClient` is the only object that touches the network | the key cannot leak through a log line, and the provider can be swapped in one place |
| **Exception handling** | `CoachError`, `LanguageModelUnavailable`, `CacheUnavailable` | the parts say precisely what failed; `explain` catches the one the user must not see |
| **Dataclasses** | `Explanation`, `Summary`, `CoachConfig` | frozen objects cross the subsystem boundary, so no caller can mutate the answer of another |

## Why is there an abstract class for the cache and for the explainer?

| Abstract class | Implementations | Why two |
|---|---|---|
| `BaseCache` | `MemoryCache`, `SQLiteCache` | the tests need a cache that leaves no file behind; the application needs one that survives a restart |
| `BaseExplainer` | `LanguageModelExplainer`, `TemplateExplainer` | the application needs an answer even when the language model cannot be reached |

`CoachService` only ever talks to the abstract class, so adding a third
implementation — a Redis cache, a different provider — changes no other file.
That is requirement N10, and `test_n10_another_provider_can_replace_the_language_model`
proves it by plugging in an explainer the package has never seen.

## Why does the coach never raise when the language model fails?

A resident standing in front of three bins needs an answer, not an error page.
`CoachService.explain` therefore catches `LanguageModelUnavailable` and asks
the `TemplateExplainer` instead, which needs no network and no key. The answer
reports where it came from in `Explanation.source`, so the web interface can
mark a template answer quietly if it wants to.

The only exception that does reach the caller is `ValueError` for an unknown
category or an empty item. That is a bug in the calling code, not a condition a
user can be in, and hiding it would hide the bug.

## Why does the cache have its own database file?

Subsystem 2 owns the project database, and its rule is that nobody outside that
package talks to SQLite directly. The cache is not shared data — it is a local
optimisation of this subsystem — so it keeps its own small file, configured
with `COACH_CACHE_PATH`. Deleting that file costs nothing but a few API calls.

## Why is the cache key built from four parts?

```
item | category | region | language
```

The same item can belong to a different bin in a different region, and the same
answer in German is a different text. Leaving any of the four out would serve a
wrong answer from the cache. `test_the_second_question_is_answered_from_the_cache`
proves the hit, `test_a_different_region_is_not_served_from_the_cache` proves
the miss.

## Why pandas and numpy for a few numbers?

The composition and the recycling rate are easy without them, but the trend is
not: it has to group by day, count per group, and fill the days where nobody
scanned anything with a zero rather than leaving a hole in the chart. That is
three lines with pandas and twenty without. The same table is then reused for
every other statistic, so the stored rows are read once per question instead of
once per number. numpy does the averaging over the resulting arrays.

## Why are the chart colours fixed per category?

Recyclable is the same green on every figure of the dashboard, so a reader does
not re-learn the legend on each one. The three colours were checked with a
colour-vision simulation: no two are confusable for protan, deutan or tritan
vision, and each has at least 3:1 contrast against the chart surface.

Colour is never the only encoding either — every bar carries its value as text,
and `charts.composition_table` returns the same numbers as a table for a reader
who cannot use the figure at all.

## What happens when there are no scans yet?

Every analytics method answers with an empty result of the right shape: an
empty DataFrame that still has its columns, an empty dict, a rate of 0.0, a
`Summary` with `total_scans=0`. The charts build from those without raising, so
the dashboard on the first day of the pilot shows an empty frame rather than a
stack trace. `test_the_charts_survive_an_empty_database` covers it.

## What this subsystem deliberately does not do

- It does not classify anything. It is told what the item is.
- It does not store the scans. It reads them through subsystem 2.
- It does not draw a page. It returns figures and objects; subsystem 4 lays
  them out.
- It does not see the photo. `explain` takes a word, which is also why no image
  ever reaches an external service.
