# Subsystem 2: Data & Rules

SQLite + SQLAlchemy database, the recycling rules of Dortmund, the rule-matching engine
and the data access layer used by the other three subsystems.

## Setup

```bash
pip install -r requirements.txt
python -m pytest            # 35 tests, in-memory database
```

The database path comes from the `DATABASE_URL` environment variable
(default: `sqlite:///data/waste.db`). In Docker, mount the folder as a volume and set,
for example, `DATABASE_URL=sqlite:////data/waste.db`.

## How the other subsystems use it

Put `src/` on the Python path (or install the package), then:

```python
from data_rules import create_services

dal, engine = create_services()   # creates the tables and loads the rules

# Which bin?
rule = engine.get_rule("recyclable", "DO")      # -> Rule(category, region_code, bin, reason)

# Store a classification (Subsystem 1 gives item, category, confidence)
dal.save_result("plastic bottle", "recyclable", 0.93, "DO")

# Data for the dashboard (Subsystem 3)
records = dal.get_results(region_code="DO", since=some_datetime)   # list[ClassificationRecord]
```

## Contract (agree this with the team before coding)

| Call | Returns |
|---|---|
| `engine.get_rule(category, region)` | `Rule(category, region_code, bin, reason)` |
| `dal.save_result(item, category, confidence, region_code, user_id=None)` | `int` (new row id) |
| `dal.get_results(region_code=None, since=None, until=None)` | `list[ClassificationRecord]` |
| `dal.get_rules(region_code)` | `list[Rule]` |
| `dal.list_regions()` | `list[(code, name)]` |

- `category` is always `"recyclable"`, `"compostable"` or `"landfill"`.
- `region` is a short code. The only seeded region is `"DO"` (Dortmund). Case does not matter.
- `confidence` is a float from 0 to 1.
- Unknown region or missing rule: `get_rule` returns a generic answer and logs a warning, it does not crash.
- Unknown category: `ValueError`.
- Nobody outside this package imports `models.py` or talks to SQLite directly.

## Tables

`user`, `item`, `classification_result`, `region`, `rule`
(one rule per region and category, enforced by a unique constraint; foreign keys are switched on).
Diagrams are in `docs/`.

## Rules are data, not code

`src/data_rules/rules/dortmund.json` holds the region and its three rules.
To add a city, add another JSON file in the same format (or point `RULES_DIR` to another folder)
and run the seed. No Python change is needed. The seed can run many times without duplicates.

Where each Dortmund rule comes from: `docs/RULE_SOURCES.md`.

## Known limit

The classifier gives three categories, but in Dortmund "recyclable" has three destinations
(yellow bin, blue paper bin, glass container). The rule text lists all three. If the team wants one exact bin,
Subsystem 1 must also send the material (plastic, paper, glass, metal) and the `rule` table needs one more column.
