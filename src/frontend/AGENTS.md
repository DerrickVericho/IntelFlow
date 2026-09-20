# Frontend Rules

- The frontend is responsible for presentation and user interaction only.
- Never call the Sectors API directly from browser code or expose API keys.
- Obtain analysis data only through backend endpoints.
- Do not recalculate scoring formulas in the frontend.
- Follow `docs/UI_SPEC.md` and approved wireframes when they are available;
  update the relevant UI documentation when the current chat changes a UI
  decision.
- Keep Broker Flow Score, Fundamental Support Score, and Combined Score visible
  separately, with their evidence and applicable data dates/windows.
- Make loading, empty, invalid-ticker, unavailable-data, and API-error states
  explicit and understandable.
- Use non-advisory language; avoid buy, sell, hold, target-price, or allocation
  wording.
- Score color must not be the only indicator; always show the numeric 0–100
  value.

