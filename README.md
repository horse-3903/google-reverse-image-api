<div align="center">

# google-reverse-image-api

Google Images scraper and REST API: original full-size image URLs and dimensions for any search, no API key, no clicking

[![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Playwright](https://img.shields.io/badge/Playwright-2EAD33?style=flat-square&logo=playwright&logoColor=white)](https://playwright.dev/python)
[![License](https://img.shields.io/github/license/horse-3903/google-reverse-image-api?style=flat-square)](LICENSE)
[![Last Commit](https://img.shields.io/github/last-commit/horse-3903/google-reverse-image-api?style=flat-square)](../../commits)

</div>

---

## Overview

**google-reverse-image-api** is a Google Images scraper that returns the original, full-size image URLs for a text search, along with their pixel dimensions, as JSON. Google embeds these URLs in the result data of the search page and its scroll responses, so the scraper reads them directly instead of clicking every thumbnail. A real Chrome is attached over the DevTools protocol (CDP) because Google serves an empty page to plain HTTP clients.

It searches Google Images by text query. It does not do upload-based reverse image search.

---

## Why This Approach

| Approach | Cost per result | Limitation |
|----------|-----------------|------------|
| Click-based Selenium or Playwright scrapers | One click and wait per thumbnail | Slow, breaks when the viewer UI changes |
| Plain `requests` or `curl` | Cheap | Google returns a JavaScript-required stub with no results |
| **This project** | Parsed from data the page already loaded | Needs a local Chrome |

Measured once on the query "test": 400 results with dimensions in about 30 seconds, including Chrome attach and scrolling.

---

## Features

- **No clicking** - full-size URLs and dimensions are parsed from the page data and scroll responses
- **Real Chrome over CDP** - launches a dedicated profile, or attaches to your main Chrome
- **All results mode** - `num=0` keeps scrolling until Google has nothing more to show
- **Background task queue** - Celery + Redis decouple request handling from scraping latency
- **Polling endpoint** - clients check task status and retrieve results when ready

---

## Tech Stack

[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![Celery](https://img.shields.io/badge/Celery-37814A?style=for-the-badge&logo=celery&logoColor=white)](https://docs.celeryq.dev)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io)
[![Playwright](https://img.shields.io/badge/Playwright-2EAD33?style=for-the-badge&logo=playwright&logoColor=white)](https://playwright.dev/python)

---

## Getting Started

### Prerequisites

- Python 3.10+
- Google Chrome
- Redis server running on `localhost:6379` (API mode only)

### Installation

```bash
pip install -r requirements.txt
```

### Run from the command line

```bash
python api/api_util.py "golden retriever" --num 50 --out results.json
```

The first run opens a Chrome window with its own profile (`~/.google-reverse-image-profile`). If Google shows a bot check, solve it in that window and rerun; the profile remembers it.

### Run the API

```bash
# Terminal 1: Celery worker
cd api && celery -A api_util worker --loglevel=info

# Terminal 2: Flask API
cd api && python app.py
```

### Run the tests

```bash
python -m unittest tests.test_extract
```

---

## API Reference

### Submit a search

```
GET /api-route/google-reverse-search/search-query?query=<query>&num=<count>
```

| Parameter | Type  | Description                                              |
|-----------|-------|----------------------------------------------------------|
| `query`   | `str` | Search query                                             |
| `num`     | `int` | Number of results, default 10, `0` for every result      |

**Response `202`:**

```json
{ "task_id": "abc123..." }
```

### Poll task status

```
GET /api-route/task-status/<task_id>
```

**Response (success):**

```json
{
  "state": "SUCCESS",
  "result": [
    { "url": "https://oxfordlearning.com/.../types-of-test-takers.jpeg", "width": 1500, "height": 1000 }
  ]
}
```

### Using the `GoogleReverseSearch` class directly

```python
import asyncio
from api.api_util import GoogleReverseSearch

results = asyncio.run(GoogleReverseSearch().search_query("golden retriever", num=10))
```

---

## Chrome Connection

| `CDP_ENDPOINT` | Behaviour |
|----------------|-----------|
| `launch` (default) | Starts Chrome with `--remote-debugging-port` and a dedicated profile, then attaches |
| `auto` | Attaches to your main Chrome after you enable `chrome://inspect/#remote-debugging` and click Allow |
| `http://...` or `ws://...` | Attaches to the given endpoint |

Chrome 136+ ignores the debugging port on the default profile, which is why `launch` uses its own profile.

---

## Project Structure

```
google-reverse-image-api/
├── api/
│   ├── app.py          # Flask application + route definitions
│   └── api_util.py     # Chrome launcher, result parser, GoogleReverseSearch, Celery task, CLI
├── tests/
│   └── test_extract.py # Parser tests for the page and scroll response formats
└── requirements.txt
```

---

## Environment Variables

| Variable         | Default                           | Description                                   |
|------------------|-----------------------------------|-----------------------------------------------|
| `REDIS_URL`      | `redis://localhost:6379/0`        | Celery broker and result backend              |
| `CDP_ENDPOINT`   | `launch`                          | `launch`, `auto`, or a CDP http/ws endpoint   |
| `CDP_PORT`       | `9333`                            | Debugging port for the launched Chrome        |
| `CHROME_PROFILE` | `~/.google-reverse-image-profile` | User data directory for the launched Chrome   |
| `CHROME_PATH`    | auto-detected                     | Path to the Chrome executable                 |

---

## Disclaimer

Automated scraping of Google Search may violate Google's Terms of Service. Use this for research and personal projects, keep request volume low, and respect the copyright and licence of every image you download. The parser depends on an undocumented page format and can break without notice.

---

## License

MIT, see [LICENSE](LICENSE)
