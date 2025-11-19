# Vercel Deployment Guide

This guide walks you through deploying the Tavily Polymarket Signals frontend to Vercel.

## Prerequisites

- A Vercel account (sign up at [vercel.com](https://vercel.com))
- Your backend API deployed and accessible (or running locally for testing)
- GitHub repository connected (already done: `prophecy-pred-markets`)

## Deployment Methods

### Method 1: Deploy via Vercel Dashboard (Recommended)

1. **Go to Vercel Dashboard**
   - Visit [vercel.com/new](https://vercel.com/new)
   - Sign in with your GitHub account

2. **Import Your Repository**
   - Click "Import Project"
   - Select `konstantinosanagn/prophecy-pred-markets` from your GitHub repositories
   - Click "Import"

3. **Configure Project Settings**
   
   Vercel should auto-detect Next.js, but verify these settings:
   
   - **Framework Preset:** Next.js
   - **Root Directory:** `frontend` (IMPORTANT!)
   - **Build Command:** `npm run build` (runs in frontend directory)
   - **Output Directory:** `.next` (default)
   - **Install Command:** `npm install` (runs in frontend directory)

4. **Set Environment Variables**
   
   Click "Environment Variables" and add:
   
   ```
   BACKEND_URL=https://your-backend-api-url.com
   ```
   
   **Important Notes:**
   - Replace `https://your-backend-api-url.com` with your actual backend URL
   - If backend is on Heroku/Railway/etc., use that URL
   - For development, you can use `http://localhost:8000` (but this won't work in production)
   - Make sure your backend CORS settings allow your Vercel domain

5. **Deploy**
   - Click "Deploy"
   - Wait for the build to complete (usually 2-3 minutes)
   - Your app will be live at `https://your-project-name.vercel.app`

### Method 2: Deploy via Vercel CLI

1. **Install Vercel CLI**
   ```bash
   npm install -g vercel
   ```

2. **Login to Vercel**
   ```bash
   vercel login
   ```

3. **Navigate to Frontend Directory**
   ```bash
   cd frontend
   ```

4. **Deploy**
   ```bash
   vercel
   ```
   
   Follow the prompts:
   - Link to existing project or create new
   - Confirm settings
   - Deploy

5. **Set Environment Variables**
   ```bash
   vercel env add BACKEND_URL
   ```
   Enter your backend URL when prompted.

6. **Redeploy with Environment Variables**
   ```bash
   vercel --prod
   ```

## Environment Variables

### Required for Frontend

| Variable | Description | Example |
|----------|-------------|---------|
| `BACKEND_URL` | Your backend API URL | `https://api.example.com` |

### Setting Environment Variables in Vercel

1. Go to your project dashboard on Vercel
2. Click "Settings" → "Environment Variables"
3. Add each variable:
   - **Key:** `BACKEND_URL`
   - **Value:** Your backend URL
   - **Environment:** Production, Preview, Development (select all)
4. Click "Save"

## Backend CORS Configuration

**IMPORTANT:** Your backend must allow requests from your Vercel domain.

Update `backend/app/main.py` CORS settings:

```python
# In production, add your Vercel domain
allowed_origins_str = os.getenv(
    "CORS_ORIGINS", 
    "http://localhost:3000,https://your-project.vercel.app"
)
```

Or set the `CORS_ORIGINS` environment variable on your backend:
```
CORS_ORIGINS=http://localhost:3000,https://your-project.vercel.app
```

## Post-Deployment Checklist

- [ ] Verify frontend builds successfully
- [ ] Set `BACKEND_URL` environment variable
- [ ] Update backend CORS to allow Vercel domain
- [ ] Test API calls from deployed frontend
- [ ] Verify all routes work correctly
- [ ] Check browser console for errors

## Troubleshooting

### Build Fails

**Error: "Cannot find module"**
- Ensure `rootDirectory` is set to `frontend` in Vercel settings
- Check that `package.json` exists in `frontend/` directory

**Error: "Build command failed"**
- Check build logs in Vercel dashboard
- Verify all dependencies are in `package.json`
- Ensure Node.js version is compatible (Vercel uses Node 18+ by default)

### API Calls Fail

**CORS Errors**
- Verify backend CORS includes your Vercel domain
- Check `CORS_ORIGINS` environment variable on backend

**404 Errors**
- Verify `BACKEND_URL` is set correctly in Vercel
- Check that backend API is accessible from the internet
- Test backend URL directly in browser/Postman

**Network Errors**
- Ensure backend is deployed and running
- Check backend logs for errors
- Verify backend URL doesn't have trailing slash issues

### Environment Variables Not Working

- Environment variables are only available at build time for Next.js
- For client-side access, use `NEXT_PUBLIC_` prefix (not needed for `BACKEND_URL` as it's server-side only)
- Redeploy after adding environment variables

## Custom Domain (Optional)

1. Go to Vercel project settings
2. Click "Domains"
3. Add your custom domain
4. Follow DNS configuration instructions

## Continuous Deployment

Vercel automatically deploys when you push to:
- `main`/`master` branch → Production
- Other branches → Preview deployments

Each push triggers a new deployment automatically!

## Monitoring

- Check deployment logs in Vercel dashboard
- Monitor function logs for API route issues
- Use Vercel Analytics (if enabled) to track performance

---

**Need Help?**
- [Vercel Documentation](https://vercel.com/docs)
- [Next.js Deployment Guide](https://nextjs.org/docs/deployment)
- Check your Vercel project dashboard for detailed logs

