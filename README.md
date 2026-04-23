# Book Website Crawler API

Book data pipeline for [books.toscrape.com](https://books.toscrape.com):

- Crawl and store book records in MongoDB
- Run scheduled re-crawls to detect changes
- Serve books and change logs through a protected FastAPI API

## Tech Stack

Python | FastAPI + Uvicorn | httpx + BeautifulSoup (lxml) + asyncio | MongoDB (motor) | APScheduler | SlowAPI + Redis | pytest + pytest-asyncio

## Project Components

1. **Crawler**
- Fetches site pages asynchronously with `httpx`
- Parses pages with `BeautifulSoup`
- Saves records to MongoDB using `motor`
- Tracks crawl progress so regular crawling can resume from the last page

2. **Scheduler**
- Uses `APScheduler (cron)` to run the crawler daily at a configured time
- Detects new books and updated books
- Optionally writes daily JSON change reports to `change_reports/`

3. **API**
- `FastAPI` app for querying books and changes
- API-key-protected endpoints
- `Rate limiting` via `SlowAPI + Redis`

4. **Tests**
- Pytest test suite for API behavior

## Requirements

- Python 3.11+
- MongoDB (local or remote)
- Redis (required for API rate limiting)

Install Python dependencies:

```bash
pip install -r requirements.txt
```

## Quick Start

1. Clone the repository.
2. Create and activate a virtual environment.

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create your environment file:

```bash
cp .env.example .env
```

5. Update `.env` values.

## Environment Variables

All variables are loaded from `.env` in the project root.

| Variable | Description | Example |
|---|---|---|
| `MONGO_URI` | MongoDB connection string | `mongodb://localhost:27017` |
| `MONGO_DB` | MongoDB database name | `book_crawler` |
| `CRAWL_URL` | Base URL for crawling | `https://books.toscrape.com` |
| `SCHEDULER_HOUR` | Scheduler hour (24h) | `12` |
| `SCHEDULER_MINUTE` | Scheduler minute | `0` |
| `GENERATE_CHANGE_REPORT` | Enable JSON report generation | `True` |
| `REDIS_URI` | Redis URI for rate limiting | `redis://localhost:6379/0` |
| `API_KEY` | API key value expected by server | `my-secret-key` |
| `API_KEY_NAME` | Header name used for API key | `API-KEY` |
| `LIMITER_FREQUENCY` | Rate-limit quota | `100` |
| `LIMITER_TIMING` | Rate-limit window unit | `hour` |

Rate-limit format is built as: `LIMITER_FREQUENCY/LIMITER_TIMING`.

## Running the Project

### 1) Run the regular crawler

```bash
python -m crawler.main
```

### 2) Run the scheduler

```bash
python -m scheduler.main
```

This process keeps running and executes the crawl on the configured cron schedule.

### 3) Run the API

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Swagger UI is available at:

- `GET /docs`

## API Authentication and Rate Limiting

- Every endpoint requires an API key header.
- Header name is taken from `API_KEY_NAME`.
- Header value must match `API_KEY`.
- Rate limiting is enforced with Redis-backed SlowAPI.

Example request header when `API_KEY_NAME=API-KEY`:

```http
API-KEY: my-secret-key
```

## API Endpoints

### `GET /books`

Returns paginated books with optional filters.

Supported query params:

- `category` (string, case-insensitive match)
- `min_price` (float)
- `max_price` (float)
- `rating` (int)
- `sort_by` (`rating` | `price` | `reviews`)
- `page` (int, default `1`)
- `page_size` (int, default `20`)

Response shape:

```json
{
	"total_count": 123,
	"page": 1,
	"books": [
		{
			"_id": "...",
			"title": "...",
			"category": "..."
		}
	]
}
```

### `GET /books/{book_id}`

Returns a single book by MongoDB ObjectId.

- `400` for invalid ObjectId format
- `404` if not found

### `GET /changes`

Returns paginated change records (latest first).

Query params:

- `page` (int, default `1`)
- `page_size` (int, default `20`)

Response shape:

```json
{
	"total_count": 45,
	"page": 1,
	"changes": [
		{
			"type": "Changed",
			"book_id": "...",
			"updated_at": "..."
		}
	]
}
```

## Running Tests

```bash
pytest -v tests/test_api.py
```

## Sample Documents

See `Sample_Documents.txt` for example data structures.


