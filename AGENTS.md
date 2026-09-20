# IntelFlow

IntelFlow is a symbol-first, flow-first market-intelligence product for IDX
stocks. It analyzes broker flow, foreign flow, shareholder changes, and
fundamental context for a selected ticker.

## Living documentation

- Read `docs/PRD.md`, `docs/SCORING.md`, and `docs/API.md` before changing
  product behavior, scoring, or Sectors API integration.
- When a product, scoring, API, architecture, or UI decision is changed through
  the current chat, update the relevant document in `docs/` in the same task.
- These documents are working drafts. Do not treat them as immutable or more
  authoritative than an explicit current user instruction.
- Apply sound engineering judgement and project-appropriate best practices when
  existing documentation is incomplete, outdated, or conflicts with the
  current request. Update the documentation after resolving the conflict.

## Project rules

- Sectors API is a core data source.
- Never commit API keys, `.env`, credentials, or logs containing secrets.
- Use `SECTORS_API_KEY` only from environment variables.
- Keep Flow Score, Fundamental Score, and Combined Score independently visible.
- Scores must be deterministic and traceable to dated Sectors inputs.
- Do not change a scoring formula without updating `docs/SCORING.md`.
- Treat `docs/API.md` as the local API contract; verify against official docs
  before adding unlisted endpoints or guessing fields.
- Do not implement automated trading, buy/sell recommendations, target prices,
  or portfolio-allocation features.
- Preserve the distinction between broker origin and investor origin.
