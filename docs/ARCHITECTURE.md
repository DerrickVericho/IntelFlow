# IntelFlow Architecture

## Sectors integration

`src/backend/sectors/` is the boundary between IntelFlow and Sectors Financial
API v2.

- `gateway.py` defines the operations required by the application.
- `client.py` handles HTTP transport, authentication, parameters, logging, and
  upstream error mapping.
- `exceptions.py` defines failures that callers can handle without depending on
  `requests` exceptions.
- Response models are intentionally deferred until representative output for
  each endpoint has been reviewed.

The Sectors layer returns raw decoded JSON for now. It must not contain scoring
or other product-level business logic.

```text
Application service -> SectorsGateway -> SectorsClient -> Sectors API
```

