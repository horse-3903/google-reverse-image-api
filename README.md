<div align="center">

# google-reverse-image-api

Async Google reverse image search via Playwright, served as a REST API with Celery task queuing

[![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/github/license/horse-3903/google-reverse-image-api?style=flat-square)](LICENSE)
[![Last Commit](https://img.shields.io/github/last-commit/horse-3903/google-reverse-image-api?style=flat-square)](../../commits)
[![Stars](https://img.shields.io/github/stars/horse-3903/google-reverse-image-api?style=flat-square)](../../stargazers)

</div>

---

## Overview

`google-reverse-image-api` is the maintained successor to `google-reverse-image-search-deprecated`. It wraps Google Images search in a headless Playwright browser, exposes the results through a Flask REST API, and offloads long-running searches to Celery workers backed by Redis. The async design handles pagination automatically until the requested number of results is collected.

## Features

- **Headless browser scraping** — Playwright drives a real Chromium instance so no API key is needed
- **Async search engine** — scrolls and paginates automatically to reach the requested result count
- **Background task queue** — Celery + Redis decouple request handling from scraping latency
- **Polling endpoint** — clients check task status and retrieve results when ready
- **Local search utilities** — additional scripts for offline/local image search workflows

## Tech Stack

[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![Celery](https://img.shields.io/badge/Celery-37814A?style=for-the-badge&logo=celery&logoColor=white)](https://docs.celeryq.dev)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io)
[![Playwright](https://img.shields.io/badge/Playwright-2EAD33?style=for-the-badge&logo=playwright&logoColor=white)](https://playwright.dev/python)

## Getting Started

### Prerequisites

- Python 3.10+
- Redis server running on `localhost:6379`

### Installation

```bash
pip install -r requirements.txt
playwright install chromium
```

### Running the Server

Start Redis, then launch a Celery worker and the Flask app in separate terminals:

```bash
# Terminal 1 — Celery worker
celery -A api.api_util worker --loglevel=info

# Terminal 2 — Flask API
python api/app.py
```

## API Reference

### Submit a reverse image search

```
GET /api-route/google-reverse-search/search-query?query=<query>&num=<count>
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `query`   | `str` | Search query or image URL |
| `num`     | `int` | Number of results to retrieve |

**Response `202`:**
```json
{ "task_id": "abc123..." }
```

---

### Poll task status

```
GET /api-route/task-status/<task_id>
```

**Response (pending):**
```json
{ "state": "PENDING", "status": "Pending..." }
```

**Response (success):**
```json
{
  "state": "SUCCESS",
  "result": ["https://...", "https://...", "..."]
}
```

---

### Using the `GoogleReverseSearch` class directly

```python
import asyncio
from api.api_util import GoogleReverseSearch

async def main():
    g = GoogleReverseSearch(debug=False)
    links = await g.search_query(query="golden retriever", num=10)
    print(links)

asyncio.run(main())
```

## Project Structure

```
google-reverse-image-api/
├── api/
│   ├── app.py          # Flask application + route definitions
│   └── api_util.py     # GoogleReverseSearch class + Celery task
├── src/
│   ├── search_api.py   # Additional API search utilities
│   ├── search_local.py # Local/offline search helpers
│   └── local_util.py   # Shared local utilities
├── data/               # Sample data (not committed)
├── test/               # Test scripts
└── requirements.txt
```

## License

MIT — see [LICENSE](LICENSE)
