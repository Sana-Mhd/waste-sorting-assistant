# Interface prototype — Subsystem 3

What subsystem 3 looks like from the outside. Subsystem 4 needs nothing from
this document except the first section.

## 1. The whole interface, in one screen

```python
from data_rules import create_services          # subsystem 2
from coach import create_coach_services, charts  # subsystem 3

dal, rule_engine = create_services()
coach, analytics = create_coach_services(dal, rule_engine)

# --- after a photo has been classified -------------------------------------
answer = coach.explain(item="plastic bottle", category="recyclable", region_code="DO")

answer.text          # "Plastic bottles can be recycled. Please put them in the ..."
answer.bin           # "Yellow bin (Wertstofftonne)"
answer.category      # "recyclable"
answer.region_code   # "DO"
answer.source        # "model" | "cache" | "template"

# the object subsystem 1 returns can be passed straight in
answer = coach.explain_result(classification_result, region_code="DO")

# --- the municipality dashboard ---------------------------------------------
summary = analytics.summary("DO")
summary.total_scans          # 128
summary.recycling_rate       # 77.8
summary.composition          # {"recyclable": 55.6, "compostable": 22.2, "landfill": 22.2}
summary.average_confidence   # 88.4

charts.composition_chart(analytics, "DO")              # plotly Figure
charts.trend_chart(analytics, "DO", days=14)           # plotly Figure
charts.top_items_chart(analytics, "DO", limit=5)       # plotly Figure
charts.composition_table(analytics, "DO")              # pandas DataFrame
```

## 2. Signatures

```python
create_coach_services(data_access, rule_engine, config=None) -> tuple[CoachService, AnalyticsService]

class CoachService:
    explain(item: str, category: str, region_code: str) -> Explanation
    explain_result(result, region_code: str) -> Explanation
    status() -> dict

class AnalyticsService:
    summary(region_code: str | None = None) -> Summary
    composition(region_code: str | None = None) -> dict[str, float]
    recycling_rate(region_code: str | None = None) -> float
    average_confidence(region_code: str | None = None) -> float
    trend(region_code: str | None = None, days: int = 14) -> pandas.DataFrame
    top_items(region_code: str | None = None, limit: int = 5) -> pandas.DataFrame
    total_scans(region_code: str | None = None) -> int
    frame(region_code=None, since=None, until=None) -> pandas.DataFrame

charts.composition_chart(analytics, region_code=None) -> plotly.graph_objects.Figure
charts.trend_chart(analytics, region_code=None, days=14) -> plotly.graph_objects.Figure
charts.top_items_chart(analytics, region_code=None, limit=5) -> plotly.graph_objects.Figure
charts.composition_table(analytics, region_code=None) -> pandas.DataFrame
```

## 3. The objects that cross the boundary

```python
@dataclass(frozen=True)
class Explanation:
    text: str           # the sentence shown to the user, at most 60 words
    bin: str            # the bin the local rule points at
    category: str       # "recyclable" | "compostable" | "landfill"
    region_code: str    # "DO"
    source: str         # "model" | "cache" | "template"

@dataclass(frozen=True)
class Summary:
    region_code: str | None
    total_scans: int
    recycling_rate: float        # percent
    composition: dict[str, float]  # percent per category
    average_confidence: float      # percent
```

`trend()` returns a DataFrame with the columns `date`, `scans`, `recycled`;
`top_items()` one with `item`, `scans`.

## 4. Rules of the interface

- `category` is one of the three categories of subsystem 2. Anything else
  raises `ValueError` — that is a bug in the caller, not a user mistake.
- `region_code` is the short code of subsystem 2, e.g. `"DO"`. Case and
  surrounding spaces do not matter.
- `explain` never raises because of the language model. When the model cannot be
  reached the text is built from the local rule and `source` says `"template"`.
- An empty `item` raises `ValueError`.
- Percentages are rounded to one decimal, so a composition can add up to 99.9.
- Passing `region_code=None` to the analytics means "every region".

## 5. What subsystem 4 writes in Flask

The services are built once, when the app starts:

```python
from flask import render_template
from data_rules import create_services
from coach import create_coach_services, charts

dal, rule_engine = create_services()
coach, analytics = create_coach_services(dal, rule_engine)
```

The result page:

```python
result = engine.classify(uploaded_photo)        # subsystem 1
answer = coach.explain_result(result, region_code)
dal.save_result(result.material, result.category, result.confidence, region_code)

return render_template("scan.html", answer=answer)
```

```html
<p>Put it in the <strong>{{ answer.bin }}</strong></p>
<p>{{ answer.text }}</p>
{% if answer.source == "template" %}
  <p>Offline answer, built from the local rule.</p>
{% endif %}
```

The dashboard page. Each chart becomes a piece of HTML, and the page loads the Plotly script once:

```python
def chart_html(figure) -> Markup:
    return Markup(figure.to_html(full_html=False, include_plotlyjs=False))

return render_template(
    "dashboard.html",
    summary=analytics.summary(region_code),
    composition=chart_html(charts.composition_chart(analytics, region_code)),
    trend=chart_html(charts.trend_chart(analytics, region_code, days=14)),
    top_items=chart_html(charts.top_items_chart(analytics, region_code)),
    table=charts.composition_table(analytics, region_code),
)
```

```html
<p>Total scans: {{ summary.total_scans }}</p>
<p>Recycling rate: {{ summary.recycling_rate }} %</p>
<p>Average confidence: {{ summary.average_confidence }} %</p>

{{ composition }}
{{ trend }}
{{ top_items }}
```

`table` is a pandas DataFrame with the same numbers, for a table under the charts.

## 6. What the user sees

The coach contributes two blocks to the result page:

```
┌──────────────────────────────────────────────────────────────┐
│  ♻  Plastic bottle                       93 % confident      │
│                                                              │
│  ✅  Put it in the Yellow bin (Wertstofftonne)               │
│                                                              │
│  Plastic bottles can be recycled. Please put them in the     │
│  yellow bin. Empty and squash the bottle first so it takes   │
│  less space, and leave the cap on.                           │
└──────────────────────────────────────────────────────────────┘
```

and three figures plus three numbers to the dashboard page:

```
┌───────────────┬───────────────┬───────────────┐
│ Total scans   │ Recycling     │ Average       │
│      128      │   77.8 %      │   88.4 %      │
└───────────────┴───────────────┴───────────────┘

┌──────────────────────────┐  ┌──────────────────────────┐
│  Waste composition       │  │  Scans over 14 days      │
│  ▇▇▇▇▇▇▇ 55.6 %          │  │        ╭──╮              │
│  ▇▇▇ 22.2 %              │  │   ╭────╯  ╰───╮          │
│  ▇▇▇ 22.2 %              │  │ ──╯           ╰──        │
└──────────────────────────┘  └──────────────────────────┘
```

The layout is subsystem 4's decision; what this subsystem guarantees is the
content of those blocks.
