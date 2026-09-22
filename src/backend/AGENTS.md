# Backend Rules

- Read and update `src/backend/API_CONTRACT.md` when adding, changing, or
  removing an endpoint consumed by the frontend.
- Read `docs/API.md` and `docs/SCHEMA.md` before adding or changing a Sectors
  API request or response model.
- Keep all Sectors API calls server-side and use `SECTORS_API_KEY` only from
  environment variables.
- Check the cache before calling paid endpoints.
- Cache complete raw Sectors JSON in Redis; keep provider validation, domain
  mapping, and scoring outside the cache implementation.
- Do not automatically retry 400, 404, or 429 responses.
- Request only required Company Report sections.
- Keep raw API retrieval, transformation, scoring, and response serialization
  separate.
- Keep domain models and public API schemas split by product section. Put only
  genuinely shared records and envelope fields in `base.py` or `common.py`.
- Define backend exceptions under `src/backend/exceptions/` by subsystem rather
  than declaring exception classes inside services, cache, configuration, or
  provider transport modules.
- Implement scoring deterministically according to `docs/SCORING.md`.
- Return score components, evidence, input dates, and calculation version with
  every analysis response.
- Do not infer investor identity from broker codes.
- Return partial results only with explicit unavailable components when an
  endpoint lacks data.
- Use clear, typed exceptions for validation, upstream API, rate-limit, and
  unavailable-data failures. Convert them into safe, useful API responses.
- Log request failures, cache outcomes, upstream status codes, and unexpected
  exceptions with enough context to debug. Never log API keys, credentials, or
  sensitive response content.
- LLM or web-research output must not modify deterministic numeric scores.
