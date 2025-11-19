## Persistent Snapshot Schema

Every analysis run is treated as an immutable experiment snapshot composed of three
core collections (plus an optional trace collection). This ensures we can
reconstruct what the market looked like, what the model believed, and what
decision the strategy took at any point in time.

### `events`

- **Purpose:** Slow-changing macro questions (e.g., “Fed decision in December?”).
- **Uniqueness:** `slug` (unique index).
- **Document shape:**

```
{
  "_id": ObjectId,
  "gamma_event_id": "35090",
  "slug": "fed-decision-in-december",
  "title": "Fed decision in December?",
  "description": "...",
  "category": "Macro",
  "image": "https://...",
  "end_date": "2025-12-10T00:00:00Z",
  "created_at": "...",
  "updated_at": "..."
}
```

We only set descriptive fields on insert (`$setOnInsert`) so the original wording
is preserved even if the upstream source edits it later.

### `markets`

- **Purpose:** Tradable contracts that belong to an event.
- **Uniqueness:** `slug` and `polymarket_url`.
- **Document shape:**

```
{
  "_id": ObjectId,
  "event_id": ObjectId,         // reference to events._id
  "gamma_market_id": "570360",
  "slug": "fed-decision-in-december-50bps",
  "polymarket_url": "https://polymarket.com/event/...",
  "question": "Fed decreases interest rates by 50+ bps...",
  "outcomes": ["Yes", "No"],
  "yes_index": 0,
  "group_item_title": "50+ bps decrease",
  "created_at": "...",
  "updated_at": "..."
}
```

### `runs`

- **Purpose:** Canonical “experiment snapshot” for a single analysis execution.
- **Indexes:** `market_id + run_at`, `event_id + run_at`, `slug`.
- **Document shape (key sections abbreviated for clarity):**

```
{
  "_id": ObjectId,
  "market_id": ObjectId,
  "event_id": ObjectId,
  "polymarket_url": "https://polymarket.com/event/...",
  "slug": "fed-decision-in-december-50bps",
  "run_at": "2025-11-15T15:10:00Z",
  "horizon": "24h",
  "strategy_preset": "Balanced",
  "strategy_params": {
    "min_edge_pct": 0.08,
    "min_confidence": "medium",
    "max_capital_pct": 0.15
  },
  "market_snapshot": { ... },   // Bid/ask, volume, liquidity, etc.
  "event_context": { ... },     // Title/description/category frozen at run time
  "news_context": { ... },      // Tavily queries + article snippets + summary
  "signal": { ... },            // Direction, probabilities, rationale
  "decision": { ... },          // BUY/SELL/HOLD, edge_pct, toy_kelly_fraction
  "report": { ... },            // Title + markdown for email/UI
  "env": { ... },               // app_version, model, tavily_version, graph version
  "created_at": "...",
  "updated_at": "...",
  "trace_id": ObjectId | null   // optional pointer into traces collection
}
```

### `traces` (optional)

- **Purpose:** Store large raw LangGraph traces without bloating the run record.
- **Document shape:**

```
{
  "_id": ObjectId,
  "run_id": ObjectId,
  "created_at": "2025-11-15T15:10:00Z",
  "steps": [...],     // raw agent step-by-step payloads
  "raw_state": {...}, // any debug blob you want to preserve
  "metadata": {...}
}
```

Runs always reference events and markets (via ObjectId) and denormalise human
readable snippets so downstream systems (backtests, notifications, UI) have a
self-contained snapshot to reason about—even if the upstream market changes.

