# health-check-service

A Python service that monitors 3 endpoints in the background and exposes their health status na dmetrics via a '/health' route 

## What It Does

- Monitors **Google**, **Netflix**, and **Apple** every 30 seconds in the background
- Exposes a `/health` endpoint that returns:
  - Overall status (`healthy`, `degraded`, or `unhealthy`)
  - Per-endpoint status, response time, HTTP code, and last check time
  - Consecutive failure count per endpoint
- Returns proper HTTP status codes (`200` / `207` / `503`) so external tools can act on the result

---

## Tech Stack

- **Python 3**
- **Flask** — web framework for exposing the `/health` endpoint
- **Requests** — for making HTTP calls to monitored endpoints
- **Threading** — for parallel endpoint checks and background monitoring

---

## How to Run

```bash
# 1. Clone the repository
git clone https://github.com/34fynn/health-check-service.git
cd health-check-service

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the service
python app.py
```

The service listens on port `5000`.

---

## Endpoints

| Route | Description |
|---|---|
| `GET /` | Confirms the service is running |
| `GET /health` | Returns health metrics for all monitored endpoints |

---

## Example Response

```json
{
  "service": "health-check-service",
  "overall_status": "healthy",
  "summary": { "total": 3, "up": 3, "down": 0 },
  "timestamp": "2026-05-11T14:05:31+00:00",
  "checks": {
    "Google":  { "status": "up", "response_time_ms": 669.27, "status_code": 200 },
    "Netflix": { "status": "up", "response_time_ms": 1855.66, "status_code": 200 },
    "Apple":   { "status": "up", "response_time_ms": 699.79, "status_code": 200 }
  }
}
```

---

## Configuration

All settings are at the top of `app.py`:

| Setting | Default | Description |
|---|---|---|
| `ENDPOINTS` | Google, Netflix, Apple | URLs to monitor |
| `REQUEST_TIMEOUT` | 5 seconds | Max wait time per check |
| `CHECK_INTERVAL` | 30 seconds | How often to re-check endpoints |

---

## Overall Status Logic

| Status | Meaning |
|---|---|
| `healthy` | All endpoints are up |
| `degraded` | Some endpoints are up, some are down |
| `unhealthy` | All endpoints are down |

