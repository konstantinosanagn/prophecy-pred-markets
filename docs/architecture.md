## Architecture overview

- **Core flow**: Frontend → Backend → Agents → Tavily / Polymarket / OpenAI → MongoDB → Frontend.
- **Backend**: FastAPI app in `backend/app`, multi-agent orchestration in `backend/app/agents`.
- **DB**: MongoDB Atlas, accessed via `pymongo` helpers in `backend/app/db`.
- **Frontend**: Next.js app in `frontend/` with a dashboard, per-market history view, and charts.


