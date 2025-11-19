## Deployment notes

- **Backend on Elastic Beanstalk**:
  - Python platform with `backend/Procfile` and `backend/runtime.txt`.
  - MongoDB connection via `MONGODB_URI` environment variable.
  - Redis cache via `REDIS_URL` or `REDIS_HOST` environment variables (optional).
  - See [Redis AWS Setup Guide](./redis-aws-setup.md) for detailed Redis configuration.
- **Frontend**:
  - Recommended: deploy Next.js app (in `frontend/`) on Vercel or similar.

## Quick Deployment Steps

### Backend (Elastic Beanstalk)

1. **Install EB CLI** (if not already installed):
   ```bash
   pip install awsebcli
   ```

2. **Initialize EB** (from `backend/` directory):
   ```bash
   cd backend
   eb init
   ```

3. **Create environment**:
   ```bash
   eb create tavily-backend-env
   ```

4. **Set environment variables**:
   ```bash
   eb setenv OPENAI_API_KEY=your_key \
            TAVILY_API_KEY=your_key \
            MONGODB_URI=your_mongodb_uri \
            USE_REDIS_CACHE=true \
            REDIS_HOST=your-redis-endpoint.cache.amazonaws.com \
            REDIS_PORT=6379
   ```

5. **Deploy**:
   ```bash
   eb deploy
   ```

### Redis Setup

For Redis configuration on AWS Elastic Beanstalk, see the detailed guide:
- **[Redis AWS Setup Guide](./redis-aws-setup.md)**


