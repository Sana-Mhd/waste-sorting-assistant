# AI-Powered Waste Sorting & Recycling Assistant

Capstone project — Compact Programming Course with Python
University of Applied Sciences and Arts Dortmund, winter 2026

A resident photographs a waste item. The system classifies it as recyclable,
compostable or landfill, looks up the recycling rule of their region, and
explains in plain language why it belongs in that bin. Every scan feeds a
dashboard where the municipality can see what is being thrown away.

**Subtopic:** a household waste assistant for residents of Dortmund, using the
recycling rules of North Rhine-Westphalia.

## Team and subsystems

| # | Subsystem | Folder | Owner |
|---|-----------|--------|-------|
| 1 | Classification Engine | `src/classification/` | |
| 2 | Data & Rules | `src/data/` | |
| 3 | AI Coach & Analytics | `src/coach/` | |
| 4 | Web Interface & Deployment | `src/web/` | |

## Interfaces between the subsystems

These three signatures are fixed. As long as they hold, all four of us can
work in parallel.

```python
classify(image_path: str) -> Classification       # subsystem 1
Repository.get_rule(category, region) -> Rule     # subsystem 2
CoachService.explain(item, region) -> str         # subsystem 3
```

## Getting started

```bash
git clone <repository url>
cd waste-sorting-assistant

python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
cp .env.example .env          # then put your real OpenAI key in .env

streamlit run src/web/app.py
```

The application runs today: every subsystem still returns a stand-in answer,
marked with `TODO` in the code. Each of us replaces our own stand-in with the
real implementation.

## Tests

```bash
python -m pytest tests/ -v
```

## Screencast

_Link to the 7-minute screencast goes here before the final upload._
