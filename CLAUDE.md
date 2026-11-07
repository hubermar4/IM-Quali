# CLAUDE.md

IRONMAN / IRONMAN 70.3 World Championship qualification analysis: historical
results → qualification targets, course factors and a static HTML dashboard
(`dist/dashboard.html`, deployed to GitHub Pages). See `README.md` for the
user-facing description.

## Commands

```bash
python -m pip install -r requirements.txt          # pandas, matplotlib, openpyxl
python -m unittest discover -s tests               # full suite, ~3 min (builds all datasets)
python -m unittest tests.test_qualification_rules  # fast, rule-level tests
python -m unittest tests.test_dashboard_features.DashboardShareableStateTests  # single class
python build.py                                    # regenerate dist/ (~3 min)
python build.py --with-tests                       # tests, then build
python -m http.server 8000 --directory dist        # view http://localhost:8000/dashboard.html
```

Node.js is used by the UI tests (they pipe extracted JS functions into `node`);
those tests are skipped when `node` is missing. Python 3.12+.

## Layout

- `src/build_dashboard.py` – loads every race-year, builds both objectives,
  Kona/Nice traces, course factors and backtest, writes `dist/`.
- `src/qualification_common.py` – parsing, cleaning, winner/pool ranking and the
  official-flag check shared by `qualification_full.py` (140.6, one total
  allocation split by starters) and `qualification_703.py` (70.3, per-gender quotas).
- `src/kona_trace.py` – World Championship start-list matching, density / scan /
  matched-slot estimators.
- `src/course_difficulty.py`, `src/gpx_course_model.py` – standard-course factors.
- `src/dashboard_template.html`, `dashboard.css`, `dashboard_app.js`,
  `dashboard_explorer.js`, `dashboard_ui.js` – inlined into one HTML file by
  `build_html()`; placeholders in `dashboard_app.js` put the explorer and UI
  files inside the app script's scope (never write the placeholder text in
  comments). `dashboard_explorer.js` is the Race Explorer (overview,
  filters, ranks, athlete detail); `dashboard_ui.js` builds the workspace shell.
- `data/reference/*.json` – hand-edited reference data (slots, standards, rule
  sets, cut-offs, calendar), loaded via `src/reference_data.py`.
- `data/race_history/<EVENT>/*.csv` – one folder per event; the year comes from
  the file name. A folder name containing `703` makes it a 70.3 event.
- `docs/` – rules, sources and review notes. `dist/` – generated; never hand-edit.

## Domain rules — read before changing qualification logic

The authoritative policy lives in `.github/instructions/` (shared with Copilot).
Read the matching file **before** touching the listed areas:

| Instruction file | Read before changing |
|---|---|
| `dual-objectives.instructions.md` | anything about targets, chances, Race Finder, cut-offs (objective A `"current"` vs B `"historical"` — never mix) |
| `qualification-rules.instructions.md` | rule sets per cycle, age grading, allocation, `qualification_*.py`, `kona_trace.py` |
| `roll-down-approaches.instructions.md` | strict / matched-slot / density / scan / rank-factor methods |
| `qualification-race-slots.instructions.md` | which races offered how many slots, scrapers, slot history doc |
| `standard-course.instructions.md` | course factors, GPX model, standard-course conversion |

Key invariants:

- Every qualification number belongs to exactly one objective and is labelled so.
  A = current P1 rules + latest allocation applied to old results; B = each
  race-year's own cycle, slots and standard, or "unavailable".
- Map a race-year to its **qualification cycle** (not calendar year) first.
- Density and absence scan need an actual P1 race with same-cycle evidence; no
  silent strict fallback; never extrapolate beyond ranked finishers.
- The performance-pool model must reproduce the official `Qualified` flags
  exactly (`test_performance_pool_model_reproduces_official_qualifiers`).
- Commit messages for qualification changes state which objective(s) they affect,
  and shared code paths keep tests for both objectives.
- Keep `docs/race_finder.md`, `docs/standard_course.md` and
  `docs/historical_qualification_rules.md` in sync with behaviour changes.

## Conventions and gotchas

- Files use **CRLF** line endings. Preserve them when editing (the Edit tool
  does; scripted rewrites must write with `newline=""` / keep `\r\n`).
- `dist/` is committed and also rebuilt by CI. Generated files are written with
  LF so local and CI builds are byte-identical. Rebuild and commit `dist/` when
  the payload or dashboard source changes.
- Data payloads must stay under `MAX_DATA_FILE_SIZE` (95 MB). Records are stored
  column-compacted (`compact_dataset` / `expandDashboardData`); keep both
  sides in sync and covered by `DashboardShareableStateTests`.
- Do not read `dist/dashboard_data_*.js` or large CSVs whole — they are tens of
  MB on one line. Inspect with `python` / `pandas` instead.
- Large docs (`docs/historical_qualification_race_slots.md`) — grep, don't read whole.
- Browser storage keys are part of the user contract; do not rename them.
- Dashboard deep links: the URL hash (`#view=…&race=…&gender=…`) is parsed by
  `parseDashboardHash` in `dashboard_ui.js`; add new shared selections there.
