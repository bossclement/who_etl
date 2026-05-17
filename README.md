# WHO GHO ETL Pipeline

Small Python ETL that extracts life-expectancy indicators from the [WHO GHO OData API](https://ghoapi.azureedge.net/api/WHOSIS_000001), normalizes them into an analysis-friendly shape, and loads them into PostgreSQL.

Built as a take-home exercise (~3h scope): clarity and integration thinking over production polish.

## Data model

**Source:** `WHOSIS_000001` — life expectancy at birth (years), by country and year.

**Target table:** `health_metrics`

| Column         | Description                          |
|----------------|--------------------------------------|
| `country_code` | ISO-style spatial dimension (`SpatialDim`) |
| `indicator`    | WHO indicator code                   |
| `year`         | Reference year                       |
| `value`        | Numeric metric                       |

**Natural key:** `(country_code, indicator, year)` — enforced with a unique constraint and used for idempotent upserts.

This shape supports simple analytical queries (trends by country, cross-country comparison for a given year, etc.).

## Architecture

```
run.py          → orchestration, checkpointing, exit codes
app/extract.py  → paginated HTTP calls to WHO OData API
app/transform.py→ field mapping, validation, in-batch deduplication
app/load.py     → PostgreSQL upsert (ON CONFLICT DO UPDATE)
app/state.py    → resume checkpoint (`state.json`)
app/db.py       → SQLAlchemy engine / session
migrations/     → Alembic schema (`health_metrics`)
```

**Design choices**

- **Batch pagination** (`$skip` / `$top`) keeps memory bounded and makes resume straightforward.
- **Checkpoint after successful load** — if extract or load fails, `skip` is not advanced, so the pipeline can resume without duplicating loaded rows (upserts are still idempotent as a safety net).
- **Upsert on load** — re-runs update existing rows instead of failing on duplicates.
- **In-batch deduplication** — the API can return duplicate natural keys within one page; PostgreSQL rejects those in a single `INSERT … ON CONFLICT` without deduping first.

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
| Missing country, year, or value | Record skipped, warning logged |
| Invalid types / out-of-range year | Pydantic validation (`app/schemas.py`), record skipped |
| Duplicate keys in one API page | Deduped in transform (latest value kept) |
| HTTP / timeout / malformed JSON | `ETLExtractError`, checkpoint not advanced |
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
  SELECT country_code, year, value
  FROM health_metrics
  WHERE country_code = 'USA'
  ORDER BY year DESC
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
- Full dataset size is manageable with paginated in-memory batches.
- One writer process; `state.json` is sufficient for checkpointing (no distributed lock).
