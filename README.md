# Tavily Polymarket Signals

Multi-agent prediction market analysis system that uses AI agents to analyze Polymarket prediction markets and generate trading signals.

## Overview

This MVP application provides automated analysis and signal generation for Polymarket prediction markets. It aggregates news from Tavily API, processes market data, and generates trading signals using OpenAI's language models. Analysis results are stored in MongoDB and displayed in a Next.js dashboard.

### Key Features

- **Multi-Agent Analysis**: Orchestrated analysis using specialized AI agents for market data, news aggregation, signal generation, and reporting
- **Real-Time Processing**: Asynchronous phased analysis that processes markets through multiple stages
- **News Integration**: Aggregates relevant news articles from Tavily API based on market context
- **Signal Generation**: AI-powered trading signals with confidence levels and rationale
- **Market History**: Stores and displays historical analysis snapshots for backtesting
- **Interactive Dashboard**: Modern Next.js frontend with real-time polling and market selection

## Architecture

- **Backend**: FastAPI (Python 3.11) with async/await patterns
- **Frontend**: Next.js 16 with TypeScript and Tailwind CSS
- **Database**: MongoDB Atlas for persistent storage
- **Cache**: Redis (optional) or in-memory caching
- **APIs**: Integration with Polymarket Gamma API, Tavily Search API, and OpenAI API

See [docs/architecture.md](docs/architecture.md) for detailed architecture information.

## Prerequisites

- **Python**: 3.11 or higher
- **Node.js**: 18.x or higher
- **npm**: 9.x or higher (or compatible package manager)
- **MongoDB**: MongoDB Atlas account (free tier works) or local MongoDB instance
- **API Keys**:
  - OpenAI API key (required)
  - Tavily API key (required)
  - MongoDB connection string (required)
  - Redis (optional, for production)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd tavily-proj
```

### 2. Backend Setup

```bash
cd backend
python -m pip install -r requirements.txt
```

### 3. Frontend Setup

```bash
cd frontend
npm install
```

### 4. Environment Configuration

Create a `.env` file in the project root (see `.env.example` for template):

```bash
# Required API Keys
OPENAI_API_KEY=your_openai_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
MONGODB_URI=your_mongodb_connection_string_here

# Optional Configuration
LOG_LEVEL=INFO
USE_REDIS_CACHE=false
REDIS_URL=redis://localhost:6379/0
CORS_ORIGINS=http://localhost:3000
```

**Important**: The `.env` file is gitignored. Never commit API keys to version control.

## Development

### Starting the Backend

From the `backend/` directory:

```bash
# Using uvicorn directly
python -m uvicorn app.main:app --reload --port 8000

# Or using the dev server script
python dev_server.py
```

The API will be available at `http://localhost:8000` with interactive docs at `http://localhost:8000/docs`.

### Starting the Frontend

From the `frontend/` directory:

```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`.

### Quick Start Scripts

The repository includes helper scripts in the `scripts/` directory:

**Windows:**
```powershell
.\scripts\backend\start.ps1   # Start backend
.\scripts\frontend\start.ps1  # Start frontend
```

**Linux/Mac:**
```bash
./scripts/backend/start.sh    # Start backend
./scripts/frontend/start.sh   # Start frontend
```

See [scripts/README.md](scripts/README.md) for more details.

## Testing

### Backend Tests

From the `backend/` directory:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_config.py -v
```

### Frontend Tests

From the `frontend/` directory:

```bash
# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Run in watch mode
npm test -- --watch
```

## Usage

1. **Start both backend and frontend** (see Development section above)

2. **Open the dashboard** at `http://localhost:3000`

3. **Paste a Polymarket URL** into the input field:
   - Example: `https://polymarket.com/event/...`
   - Supports both event URLs and direct market URLs

4. **Select a market** (if multiple markets are available for the event)

5. **View results** as the analysis progresses through phases:
   - Market snapshot (current prices, volume, liquidity)
   - News context (aggregated relevant articles)
   - Trading signal (direction, confidence, rationale)
   - Final report (comprehensive analysis)

## API Documentation

Once the backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Main Endpoints

- `POST /api/analyze/start` - Start analysis for a market URL
- `GET /api/run/{run_id}` - Get analysis results for a run
- `GET /api/analyze` - Legacy synchronous analysis endpoint
- `GET /health` - Health check endpoint
- `GET /health/ready` - Readiness probe with dependency checks

## Deployment

### Backend Deployment

The backend is configured for deployment on AWS Elastic Beanstalk:

- `Procfile` - Defines the web server process
- `runtime.txt` - Specifies Python version
- `requirements.txt` - Python dependencies

See [docs/deployment.md](docs/deployment.md) for detailed deployment instructions.

### Frontend Deployment

The frontend can be deployed on:
- **Vercel** (recommended for Next.js)
- **Netlify**
- Any Node.js hosting platform

Set the `BACKEND_URL` environment variable to your backend URL in production.

### Environment Variables for Production

```bash
# Required
OPENAI_API_KEY=your_production_openai_key
TAVILY_API_KEY=your_production_tavily_key
MONGODB_URI=your_production_mongodb_uri

# Recommended for production
USE_REDIS_CACHE=true
REDIS_URL=your_redis_connection_string
CORS_ORIGINS=https://your-frontend-domain.com
LOG_LEVEL=WARNING
```

## Troubleshooting

### Backend Issues

**MongoDB Connection Failed**
- Verify `MONGODB_URI` is correct in `.env`
- Check network connectivity to MongoDB Atlas
- Verify MongoDB credentials are valid

**OpenAI API Errors**
- Check `OPENAI_API_KEY` is set correctly
- Verify API key has sufficient credits/quota
- Check circuit breaker status (may need reset if open)

**Import Errors**
- Ensure you're in the `backend/` directory when running commands
- Verify all dependencies are installed: `pip install -r requirements.txt`
- Check Python version: `python --version` should be 3.11+

### Frontend Issues

**Build Errors**
- Run `npm install` to ensure dependencies are installed
- Clear `.next` directory: `rm -rf .next` (Linux/Mac) or `Remove-Item -Recurse -Force .next` (Windows)
- Verify TypeScript strict mode compatibility (enabled in `tsconfig.json`)

**API Connection Errors**
- Verify backend is running on `http://localhost:8000`
- Check `BACKEND_URL` environment variable if using custom backend URL
- Verify CORS is configured correctly in backend

**Type Errors After Enabling Strict Mode**
- TypeScript strict mode is enabled. Fix any type errors that appear
- Use type assertions or optional chaining where needed
- Ensure all interfaces match actual data structures

### Common Issues

**Port Already in Use**
- Backend: Change port with `--port 8001` or kill existing process
- Frontend: Change port with `npm run dev -- -p 3001` or kill existing process

**Module Not Found**
- Backend: Reinstall dependencies with `pip install -r requirements.txt`
- Frontend: Reinstall dependencies with `npm install`

**Redis Connection Issues**
- If `USE_REDIS_CACHE=true`, ensure Redis is running
- System will fall back to in-memory cache if Redis unavailable
- Check Redis connection string format: `redis://host:port/db`

## Project Structure

```
tavily-proj/
├── backend/
│   ├── app/
│   │   ├── agents/        # Multi-agent orchestration
│   │   ├── core/          # Core utilities (cache, logging, resilience)
│   │   ├── db/            # Database clients and repositories
│   │   ├── routes/        # FastAPI route handlers
│   │   ├── schemas/       # Pydantic models
│   │   └── services/      # Business logic services
│   ├── tests/             # Backend tests
│   ├── requirements.txt   # Python dependencies
│   ├── Procfile          # Deployment configuration
│   └── runtime.txt       # Python version
├── frontend/
│   ├── app/              # Next.js App Router pages
│   ├── components/       # React components
│   ├── tests/            # Frontend tests
│   └── package.json      # Node.js dependencies
├── docs/                 # Documentation
├── scripts/              # Helper scripts
├── .env.example          # Environment variable template
└── README.md            # This file
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## MVP Scope

### Completed Features ✅

- **Multi-Agent Analysis System**: Orchestrated analysis using specialized AI agents
- **Market Data Integration**: Real-time Polymarket market data fetching and processing
- **News Aggregation**: Tavily API integration for relevant news articles
- **Signal Generation**: AI-powered trading signals with confidence levels and rationale
- **Phased Analysis**: Asynchronous processing through market → news → signal → report phases
- **Market Selection**: Support for events with multiple markets
- **Interactive Dashboard**: Next.js frontend with real-time polling and status updates
- **Data Persistence**: MongoDB storage for analysis runs and history
- **Error Handling**: Circuit breaker pattern for API resilience
- **Comprehensive Testing**: 34+ backend tests and 13+ frontend tests

### Incomplete Features / Future Work 🚧

The following features have TODO comments in the codebase and are planned for future development:

- **Outcome Extraction**: Market resolution tracking for IR value evaluation (`backend/scripts/evaluate_ir_value.py`)

### Known Limitations

- **No User Authentication**: MVP does not include user accounts or authentication
- **No Rate Limiting**: API endpoints do not have rate limiting (recommended for production)
- **Debug Endpoint**: `/debug/polymarket/{slug}` endpoint exists for development (consider disabling in production)
- **In-Memory Cache Default**: Uses in-memory caching by default (Redis optional)

## Additional Documentation

- [Architecture](docs/architecture.md) - System architecture and design
- [Data Model](docs/data_model.md) - Database schema and data structures
- [Deployment](docs/deployment.md) - Deployment instructions
- [Use Case](docs/use_case.md) - Use case and workflow description
- [Development Notes](docs/README_DEV.md) - Development server setup and tips
