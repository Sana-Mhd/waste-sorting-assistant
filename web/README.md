# Subsystem 4: Web Interface & Deployment

The Streamlit app that connects the other three subsystems, and the Docker image
that ships all four as one application.

| The user does | Behind the scenes |
|---|---|
| uploads a photo, picks a region | Subsystem 1 `ClassificationEngine.classify(bytes)` → material, category, confidence |
| sees the bin and an explanation | Subsystem 3 `CoachService.explain_result(result, "DO")`, which asks Subsystem 2 for the rule |
| (automatic) | Subsystem 2 `DataAccessLayer.save_result(...)` stores the scan |
| opens the dashboard | Subsystem 3 `AnalyticsService.summary()` and `charts.*` |

## Run with Docker (recommended)

Only Docker is needed.

```bash
docker compose up --build
```

Open http://localhost:8501. Scans and cached explanations are stored in the volume
`waste-data` (`/data` in the container), so they survive a restart.

For AI explanations, create a `.env` file next to `docker-compose.yml` (see `.env.example`)
with `OPENAI_API_KEY=...`. Without a key the coach answers from the local rules.
The key is passed at run time and never copied into the image.

## Run locally

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r web/requirements.txt
streamlit run web/src/web/app.py
```

`app.py` puts the four `src/` folders on the Python path itself, so no `PYTHONPATH` is needed.
Locally the database is `data/waste.db` in the folder you start from.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | `sqlite:///data/waste.db` (Docker: `sqlite:////data/waste.db`) | database of subsystem 2 |
| `DEFAULT_REGION` | `DO` | region preselected in the sidebar; a code or a name ("Dortmund") |
| `OPENAI_API_KEY` | *(empty)* | AI explanations; empty means offline templates |
| `COACH_CACHE_PATH` | `data/coach_cache.db` (Docker: `/data/coach_cache.db`) | explanation cache of subsystem 3 |
| `MODEL_PATH`, `CONFIDENCE_THRESHOLD`, ... | see `classification/README.md` | settings of subsystem 1 |

## Pages

- **Scan an item**: upload a JPEG/PNG. A confident result shows the material, the category,
  the bin, the explanation and the three most likely materials. An uncertain result asks for
  a new photo and is not stored, so the dashboard only counts answers the user was shown.
  A broken or too large file gets a short message instead of an error page.
  One upload is one scan: a page redraw or a change of region does not store it again.
- **Municipality dashboard**: total scans, recycling rate, average confidence, waste composition,
  trend over 14 days, most scanned items, and the numbers as a table.
- **About**: what the app does, which subsystem does what, known limits, and whether the
  real model and the OpenAI coach are active.

## Design

| File | Content |
|---|---|
| `app.py` | Streamlit entry point: page setup, sidebar, chooses a page. No logic. |
| `services.py` | `AppServices` (composition of the five services of subsystems 1–3) and `build_services()` |
| `workflow.py` | `ScanWorkflow.run(image, region) -> ScanOutcome`: classify → explain → save. No Streamlit inside. |
| `pages.py` | `BasePage` (abstract) → `ScanPage`, `DashboardPage`, `AboutPage` |
| `config.py` | `WebConfig.from_env()`, `resolve_region()` |
| `exceptions.py` | `WebError` → `ServiceStartupError` |

- **Composition:** `AppServices` holds the services; `ScanPage` holds a `ScanWorkflow`.
- **Inheritance and abstract class:** every page implements `BasePage.render(region_code)`.
- **Separation:** the logic (`workflow.py`) is plain Python and tested with pytest;
  the pages only display a `ScanOutcome`.
- **Errors:** `InvalidImageError` (subsystem 1) is shown as a friendly message;
  a failing start raises `ServiceStartupError` with a readable message;
  a failing save is logged and the user still gets the answer.

## Tests

```bash
cd web
python -m pytest -v
```

28 tests, no network, no OpenAI key, no files left behind:

| File | Covers |
|---|---|
| `test_services.py` | all services start on a temporary database, bad `DATABASE_URL`, settings, region names |
| `test_workflow.py` | confident scan is explained and saved, uncertain scan is not, every category, invalid upload, unknown region, scans reach the dashboard |
| `test_app.py` | the real `app.py` with Streamlit's `AppTest`: starts, sidebar, empty dashboard, about page, a photo is saved once per upload, the upload limit |

The workflow tests use the real subsystems 2 and 3 and a `DummyClassifier`, so they do not
depend on the trained model.

## Known limits

- One region (Dortmund) is seeded; more regions are a JSON file in `data_rules` (see its README).
- In Dortmund "recyclable" has three destinations (yellow bin, paper bin, glass container),
  so the bin text lists all three. Choosing one exact bin would need the material in the rules table.
- Streamlit runs every user in the same process; the model and database are loaded once
  (`st.cache_resource`) and shared.
