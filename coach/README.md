# Subsystem 3: AI Coach & Analytics

Two things the application needs once a photo has been classified:

1. **The coach** turns the classification plus the local recycling rule into one
   short, plain-language explanation of why the item belongs in that bin.
2. **The analytics** read the stored scans and produce the numbers and the
   figures of the municipality dashboard.

Part of the capstone project *AI-Powered Waste Sorting & Recycling Assistant*,
University of Applied Sciences and Arts Dortmund, winter 2026.

## Setup

```bash
pip install -r requirements.txt
python -m pytest                 # 83 tests, no network, no API key, no files left behind
                                 # (7 of them are skipped if subsystem 2 is not next to this folder)
```

Python 3.10 or newer.

## Configuration

Everything is read from the environment; nothing secret is in the code.

| Variable | Default | What it does |
|---|---|---|
| `OPENAI_API_KEY` | *(empty)* | the key; empty means the coach answers from the local rule |
| `OPENAI_MODEL` | `gpt-4o-mini` | which model to ask |
| `COACH_CACHE_PATH` | `data/coach_cache.db` | where stored explanations live |
| `COACH_LANGUAGE` | `en` | `en` or `de` |
| `COACH_MAX_WORDS` | `60` | upper limit of an explanation |
| `COACH_TIMEOUT` | `10` | seconds to wait for the model |

Without a key nothing breaks: the explanation is built from the local rule and
`Explanation.source` says `"template"`.

## How the other subsystems use it

```python
from data_rules import create_services          # subsystem 2
from coach import create_coach_services, charts  # subsystem 3

dal, rule_engine = create_services()
coach, analytics = create_coach_services(dal, rule_engine)

answer = coach.explain("plastic bottle", "recyclable", "DO")
answer.text          # the sentence shown to the user
answer.bin           # "Yellow bin (Wertstofftonne)"
answer.source        # "model" | "cache" | "template"

summary = analytics.summary("DO")
summary.total_scans, summary.recycling_rate, summary.composition

charts.composition_chart(analytics, "DO")       # plotly Figure
charts.trend_chart(analytics, "DO", days=14)
charts.top_items_chart(analytics, "DO", limit=5)
```

The complete interface, the Flask code and a sketch of what the user
sees are in **[docs/INTERFACE.md](docs/INTERFACE.md)**.

## Contract

| Call | Returns |
|---|---|
| `create_coach_services(dal, rule_engine)` | `(CoachService, AnalyticsService)` |
| `CoachService.explain(item, category, region_code)` | `Explanation(text, bin, category, region_code, source)` |
| `CoachService.explain_result(result, region_code)` | `Explanation` |
| `CoachService.status()` | `dict` — which explainer and cache are in use |
| `AnalyticsService.summary(region_code=None)` | `Summary(region_code, total_scans, recycling_rate, composition, average_confidence)` |
| `AnalyticsService.composition(region_code=None)` | `dict[str, float]`, percent per category |
| `AnalyticsService.recycling_rate(region_code=None)` | `float`, percent |
| `AnalyticsService.average_confidence(region_code=None)` | `float`, percent |
| `AnalyticsService.trend(region_code=None, days=14)` | `DataFrame` — `date`, `scans`, `recycled` |
| `AnalyticsService.top_items(region_code=None, limit=5)` | `DataFrame` — `item`, `scans` |
| `charts.composition_chart / trend_chart / top_items_chart` | `plotly.graph_objects.Figure` |
| `charts.composition_table(analytics, region_code=None)` | `DataFrame` — the same numbers as a table |

- `category` is always `"recyclable"`, `"compostable"` or `"landfill"` — the
  three categories of subsystem 2.
- `region_code` is the short code of subsystem 2, e.g. `"DO"`. Case and
  surrounding spaces do not matter. `None` in the analytics means every region.
- `explain` never raises because of the language model. It raises `ValueError`
  for an unknown category or an empty item, because that is a bug in the caller.
- Percentages are rounded to one decimal, so a composition can add up to 99.9.
- Nobody outside this package talks to the OpenAI API or to the cache file.

## What it needs from the other subsystems

| From | What | Used for |
|---|---|---|
| Subsystem 2 | `RuleEngine.get_rule(category, region)` | the rule the explanation is built on |
| Subsystem 2 | `DataAccessLayer.get_results(region_code, since, until)` | every statistic and figure |
| Subsystem 1 | `ClassificationResult.material` and `.category` | what to explain |

`tests/test_contract.py` fails the moment subsystem 2 renames one of those
fields, so a mismatch is found by pytest and not by a user.

## Data storage

| What | Where | Owner |
|---|---|---|
| Finished explanations | SQLite table `explanation_cache` (`key`, `text`, `created_at`) in its own file, `COACH_CACHE_PATH` | this subsystem |
| Scans, rules, regions, users | the project database | subsystem 2 — this subsystem only reads them, through `DataAccessLayer` |

The cache is a local optimisation, not shared data, which is why it has a file
of its own: subsystem 2's rule is that nobody outside that package talks to the
project database directly. Deleting the cache file costs nothing but a few API
calls. In Docker, mount the folder as a volume and set
`COACH_CACHE_PATH=/data/coach_cache.db`.

## How an explanation is produced

1. Ask subsystem 2 for the rule of this category in this region.
2. Build the cache key from item, category, region and language.
3. If the cache holds an answer, return it — under 200 ms, no cost.
4. Otherwise ask the language model, with the rule inside the prompt so it
   cannot invent a different one.
5. If the model has no key, times out or errors, build the text from the rule.
6. Store the answer and return it.

The user therefore always gets an answer, and the same item in the same region
is never paid for twice.

## Classes

| Class | Responsibility |
|---|---|
| `CoachService` | entry point: cache first, then the explainer, always an answer |
| `BaseExplainer` | abstract interface of an explainer |
| `LanguageModelExplainer` | asks the language model, cuts the answer to the word limit |
| `TemplateExplainer` | builds the text from the local rule alone; works offline, English or German |
| `OpenAIClient` | the only place in the project that calls the OpenAI API |
| `BaseCache` | abstract interface of the explanation cache |
| `MemoryCache` | cache for the tests, nothing on disk |
| `SQLiteCache` | cache of the application, survives a restart |
| `AnalyticsService` | every statistic, built on pandas and numpy |
| `charts` | the dashboard figures, one palette across all of them |
| `CoachConfig` | the settings, read from the environment, key masked when printed |
| `Explanation`, `Summary` | the frozen objects that cross the boundary |

Class diagram: **[docs/class_diagram.png](docs/class_diagram.png)**.
The reasoning behind the design, including which object-oriented concept sits
where: **[docs/DESIGN_NOTES.md](docs/DESIGN_NOTES.md)**.

## Requirements

Ten functional and ten non-functional requirements, each one proved by a named
test: **[docs/REQUIREMENTS.md](docs/REQUIREMENTS.md)**.

```bash
python -m pytest tests/test_requirements.py -v     # one test per requirement
```

## Tests

```bash
python -m pytest -v
```

83 tests, none of which need a network connection, an API key or a database
file. The last run is stored in **[reports/test_report.txt](reports/test_report.txt)**.

| File | Covers |
|---|---|
| `test_requirements.py` | one test per numbered requirement — the traceability matrix |
| `test_cache.py` | the key, both caches, surviving a restart |
| `test_coach.py` | caching, the fallback, the word limit, the prompt, bad input |
| `test_analytics.py` | composition, recycling rate, trend with empty days, top items |
| `test_charts.py` | every figure builds, also on an empty database |
| `test_contract.py` | the real `data_rules` package: field names, categories, and one end-to-end run against a temporary database |

The language model is never called: the tests use a fake explainer or the
template, which is also how the application behaves when no key is configured.
A test run leaves no file behind — the cache is redirected into pytest's
temporary directory.

## Running it in Docker

The subsystem has no Dockerfile of its own; the application is built as one
image by subsystem 4. What it needs from that image:

```dockerfile
# the dependencies of this subsystem
COPY coach/requirements.txt /tmp/coach-requirements.txt
RUN pip install --no-cache-dir -r /tmp/coach-requirements.txt

# the package on the import path
COPY coach/src/coach /app/coach
ENV PYTHONPATH=/app
ENV COACH_CACHE_PATH=/data/coach_cache.db     # mount /data as a volume
```

`OPENAI_API_KEY` is passed at run time, never baked into the image.
