# IntelFlow

## Local backend infrastructure

Copy `.env.example` to `.env`, keep the existing `SECTORS_API_KEY`, then start
Redis:

```powershell
docker compose up -d redis
docker compose ps
```

The Compose service exposes Redis only on `127.0.0.1`, persists its data in the
named `intelflow_redis-data` volume, and uses append-only persistence. Start the
backend after Redis is healthy:

```powershell
uv run uvicorn src.backend.main:app --reload
```

Stop the container without deleting cached data:

```powershell
docker compose down
```

Use `docker compose down -v` only when the Redis cache should be deleted.
