# WHO GHO ETL Pipeline

Small Python ETL that extracts life-expectancy indicators from the [WHO GHO OData API](https://ghoapi.azureedge.net/api/WHOSIS_000001), normalizes them into an analysis-friendly shape, and loads them into PostgreSQL.

Built as a take-home exercise (~3h scope): clarity and integration thinking over production polish.

## Data model

**Source:** `WHOSIS_000001` — life expectancy at birth (years), by country, year, and sex disaggregation.

**Target table:** `health_metrics`

| Column         | Description                          |
|----------------|--------------------------------------|
| `country_code` | ISO-style spatial dimension (`SpatialDim`) |
| `indicator`    | WHO indicator code                   |
| `year`         | Reference year (`TimeDim`)           |
| `sex`          | Sex disaggregation — mapped from API `Dim1` (e.g. `SEX_MLE`, `SEX_FMLE`, `SEX_BTSX`) |
| `value`        | Numeric metric (`NumericValue`)      |

**API → internal field mapping:** `SpatialDim` → `country_code`, `TimeDim` → `year`, `IndicatorCode` → `indicator`, **`Dim1` → `sex`**, `NumericValue` → `value`. The API name `Dim1` is generic; for `WHOSIS_000001` it means sex, so our schema uses `sex`.

**Natural key:** `(country_code, indicator, year, sex)` — enforced with a unique constraint and used for idempotent upserts.

### Why `sex` is part of the key

A sample of 300 rows from the live API showed three `Dim1` values (`SEX_MLE`, `SEX_FMLE`, `SEX_BTSX`) and **8 country/year combinations with more than one sex** (e.g. Denmark 2020 had both male and female rows). The original key `(country_code, indicator, year)` caused in-batch deduplication to keep only one row and **drop the others**.

`sex` is included in the schema, transform, unique constraint, and upsert so each disaggregation is stored separately. In-batch dedupe still applies only to **exact** duplicate keys (same country, indicator, year, and `sex`).

This shape supports analysis by country/year and comparisons across sex without silent data loss.

## Architecture

```
run.py          → orchestration, checkpointing, exit codes
app/extract.py  → paginated HTTP calls to WHO OData API (retries on transient errors)
app/transform.py→ field mapping, validation, in-batch deduplication
app/load.py     → PostgreSQL upsert (ON CONFLICT DO UPDATE)
app/state.py    → resume checkpoint (`state.json`)
app/db.py       → SQLAlchemy engine / session
migrations/     → Alembic schema (`health_metrics`)
```

**Design choices**

- **Batch pagination** (`$skip` / `$top`) keeps memory bounded and makes resume straightforward.
- **Fetch retries** — GET requests retry on timeouts, connection errors, and HTTP 429/5xx with exponential backoff (urllib3 via `requests`; default 3 retries, 1s backoff factor).
- **Checkpoint after successful load** — if extract or load fails, `skip` is not advanced, so the pipeline can resume without duplicating loaded rows (upserts are still idempotent as a safety net).
- **Upsert on load** — re-runs update existing rows instead of failing on duplicates.
- **In-batch deduplication** — the API can return exact duplicate natural keys within one page (same country, indicator, year, and `sex`); PostgreSQL rejects those in a single `INSERT … ON CONFLICT` without deduping first.

## Setup

**Prerequisites:** Python 3.9+, Docker (for Postgres).

1. **Start PostgreSQL**

   ```bash
   docker compose up -d
   ```

2. **Create a virtualenv and install dependencies**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure environment**

   ```bash
   cp .env.example .env
   ```

4. **Apply migrations**

   ```bash
   python -m alembic upgrade head
   ```

5. **Run the pipeline**

   ```bash
   python run.py
   python run.py --help
   ```

   Use the venv interpreter (`python` / `./venv/bin/python`), not the system `python3`, so dependencies and versions match.

### CLI options

| Flag | Description |
|------|-------------|
| `--api-url URL` | WHO OData endpoint (default: `WHOSIS_000001`) |
| `--page-size N` | Records per batch / `$top` (default: 100) |
| `--timeout SEC` | HTTP timeout (default: 30) |
| `--max-retries N` | Retries per request on transient failures (default: 3) |
| `--retry-backoff SEC` | Exponential backoff factor between retries (default: 1.0) |
| `--skip N` | Start at this `$skip` offset (overrides `state.json` for this run) |
| `--reset` | Clear checkpoint to `skip=0` before running |
| `--max-batches N` | Stop after N batches (debugging) |

Examples:

```bash
python run.py --page-size 50 --max-batches 2
python run.py --reset
python run.py --skip 5000
```

## Resume and re-runs

Progress is stored in `state.json` as `{"skip": N}`.

- **Stop / resume:** `Ctrl+C` or a failed run leaves the last successful `skip` on disk. Run `python run.py` again to continue from that offset.
- **Reset:** delete `state.json` (or set `"skip": 0`) to re-extract from the beginning.
- **Re-run / “new data”:** the pipeline does not track API change timestamps. Re-running from `skip=0` re-fetches all pages but **upserts** into Postgres, so loads are idempotent. A production version would likely use `?$filter=…` on `DateModified` or similar if the API exposes it.

## Validation and edge cases

| Case | Handling |
|------|----------|
| Missing country, year, sex (`Dim1` absent), or value | Record skipped, warning logged |
| Invalid types / out-of-range year | Pydantic validation (`app/schemas.py`), record skipped |
| Exact duplicate natural keys in one API page | Deduped in transform (latest value kept) |
| HTTP / timeout / connection errors | Retried up to `--max-retries`; then `ETLExtractError`, checkpoint not advanced |
| Malformed JSON | `ETLExtractError` (not retried), checkpoint not advanced |
| DB errors | Rollback, `ETLLoadError`, checkpoint not advanced |
| Corrupt `state.json` | `ETLStateError` on startup |

Logs are written to `logs/etl.log` and stdout.

## Testing and debugging

**Unit tests** (transform logic, no network/DB):

```bash
pytest
```

**Manual checks**

- DB connectivity: `python test_db.py`
- Inspect checkpoint: `cat state.json`
- Tail logs: `tail -f logs/etl.log`
- Sample query:

  ```sql
  SELECT country_code, year, sex, value
  FROM health_metrics
  WHERE country_code = 'USA'
  ORDER BY year DESC, sex
  LIMIT 10;
  ```

**Debugging approach:** run one or two batches with `--page-size 10 --max-batches 2`, watch log lines per stage (extract → transform → load → checkpoint), and verify row counts in Postgres after each batch.

## What I’d improve with more time

- **Incremental extract** using OData `$filter` on a modified timestamp (if reliable), instead of full re-fetch + upsert.
- **Structured config** (pydantic-settings) and retries with backoff for the API.
- **Integration tests** with HTTP mocking and a test Postgres container.
- **Orchestration** (cron, Airflow, or a job queue) and metrics (rows/sec, error rate).
- **Data quality checks** post-load (null rates, expected country/year ranges).

## Assumptions

- `WHOSIS_000001` is a stable, useful dataset for the exercise.
- `SpatialDim` is an acceptable country identifier for analysis.
- API `Dim1` values (`SEX_MLE`, `SEX_FMLE`, `SEX_BTSX`) are stored in column `sex` as returned by the API; multiple sex values per country/year are expected, not anomalies.
- Full dataset size is manageable with paginated in-memory batches.
- One writer process; `state.json` is sufficient for checkpointing (no distributed lock).
