# Pre-Submission Checklist

Use this checklist to ensure your MVP is ready for submission.

## 🔴 Critical (Must Complete)

- [x] **Remove `nul` file** from repository root ✅ **COMPLETED**
  ```bash
  git rm nul
  ```

- [ ] **Remove coverage directory** (if tracked in git)
  ```bash
  git rm -r --cached frontend/coverage
  ```

- [ ] **Create `.env.example`** file (✅ Created - verify it's correct)

- [ ] **Clean up excessive console.log statements**
  - [ ] Review `frontend/components/Background.tsx` (48+ logs)
  - [ ] Review `frontend/app/api/analyze/start/route.ts`
  - [ ] Review `frontend/app/api/run/[run_id]/route.ts`
  - [ ] Remove debug logs, keep only error logs

- [ ] **Run backend tests**
  ```bash
  cd backend
  pytest
  ```

- [ ] **Run frontend tests**
  ```bash
  cd frontend
  npm test
  ```

- [ ] **Run backend linter**
  ```bash
  cd backend
  ruff check .
  ruff format .
  ```

- [ ] **Run frontend linter**
  ```bash
  cd frontend
  npm run lint
  ```

- [ ] **Verify no secrets in repository**
  ```bash
  git grep -i "api_key" -- "*.py" "*.ts" "*.tsx" "*.js"
  git grep -i "password" -- "*.py" "*.ts" "*.tsx" "*.js"
  git grep -i "mongodb_uri" -- "*.py" "*.ts" "*.tsx" "*.js"
  ```

## 🟠 High Priority (Should Complete)

- [ ] **Move utility scripts** to proper location
  - [ ] Move `backend/test_openai_key.py` to `scripts/backend/`
  - [ ] Move `backend/reset_circuit_breaker.py` to `scripts/backend/`
  - [ ] Update any documentation referencing these scripts

- [ ] **Organize documentation**
  - [ ] Review `ENV_MIGRATION_SUMMARY.md` (archive or keep)
  - [ ] Review `REPO_REVIEW.md` (update or remove)
  - [ ] Move `backend/polymarket_api_endpoints.txt` to `docs/` or convert to `.md`

- [ ] **Document MVP scope** in README
  - [ ] List completed features
  - [ ] List incomplete features (TODOs)
  - [ ] Note any known limitations

- [ ] **Test fresh setup**
  - [ ] Clone repository to new directory
  - [ ] Follow README setup instructions
  - [ ] Verify everything works from scratch

## 🟡 Medium Priority (Nice to Have)

- [ ] **Review TODO comments** in code
  - [ ] Document in README or create roadmap
  - [ ] Or remove if not planning to implement

- [ ] **Verify deployment configs**
  - [ ] Test backend deployment (if possible)
  - [ ] Test frontend deployment (if possible)
  - [ ] Verify environment variables documented

- [ ] **Generate test coverage reports**
  ```bash
  # Backend
  cd backend
  pytest --cov=app --cov-report=html
  
  # Frontend
  cd frontend
  npm run test:coverage
  ```

## ✅ Verification Steps

- [ ] **README completeness**
  - [ ] All setup steps work
  - [ ] All required dependencies listed
  - [ ] All environment variables documented
  - [ ] Troubleshooting section helpful

- [ ] **Code quality**
  - [ ] No obvious bugs
  - [ ] Error handling in place
  - [ ] Type safety (TypeScript strict mode)
  - [ ] No hardcoded values

- [ ] **Documentation**
  - [ ] README is comprehensive
  - [ ] API docs accessible (FastAPI /docs)
  - [ ] Architecture documented
  - [ ] Deployment guide present

- [ ] **Security**
  - [ ] No secrets in code
  - [ ] .env in .gitignore
  - [ ] CORS properly configured
  - [ ] Input validation present

## 📝 Final Steps

- [ ] **Commit all changes**
  ```bash
  git add .
  git commit -m "Pre-submission cleanup"
  ```

- [ ] **Create final review**
  - [ ] Read through COMPREHENSIVE_REPO_REVIEW.md
  - [ ] Address all Critical items
  - [ ] Address High Priority items if time permits

- [ ] **Prepare submission**
  - [ ] Ensure repository is clean
  - [ ] All tests passing
  - [ ] Documentation complete
  - [ ] Ready for review

---

**Estimated Time to Complete:**
- Critical items: 2-3 hours
- High Priority: +1-2 hours
- Medium Priority: +1 hour

**Total: 4-6 hours for complete cleanup**

