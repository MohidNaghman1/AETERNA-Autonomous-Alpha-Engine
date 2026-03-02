# Pre-Deployment Checklist

## Code Quality
- [ ] All tests pass locally: `pytest tests/ -v`
- [ ] No linting issues: `flake8 app`
- [ ] Code formatted with black: `black app`
- [ ] Type hints checked: `mypy app`
- [ ] Coverage above 80%: `pytest --cov=app`

## Configuration
- [ ] `.env.example` updated with new variables
- [ ] Secrets stored in GitHub Secrets (not in code)
- [ ] Database migrations created: `alembic revision --autogenerate`
- [ ] `render.yml` reviewed and updated
- [ ] Docker image builds locally: `docker build -t aeterna:test .`

## Docker & Compose
- [ ] Dockerfile optimized (multi-stage build)
- [ ] `.dockerignore` excludes unnecessary files
- [ ] `docker-compose.yml` synced with Render services
- [ ] All services start: `docker-compose up -d`
- [ ] Health checks working
- [ ] Logs clean (no errors)

## Testing
- [ ] Unit tests: `pytest tests/`
- [ ] Integration tests with Docker services
- [ ] Load testing (optional): `locust -f tests/load_test.py`
- [ ] Manual API testing (Postman/Insomnia)

## Documentation
- [ ] README updated with deployment info
- [ ] `DEPLOYMENT_GUIDE.md` reviewed
- [ ] API docs accessible: `http://localhost:8000/docs`
- [ ] Environment variables documented

## GitHub Setup
- [ ] CI/CD workflow running successfully
- [ ] Branch protection rules enabled for `main`
- [ ] Require status checks before merge
- [ ] Code review requirements set (if needed)
- [ ] Secrets configured for Docker registry access

## Render Preparation
- [ ] Render account active
- [ ] GitHub repository connected
- [ ] Environment variables added to Render
- [ ] Database backup strategy planned
- [ ] Auto-deploy settings configured

## Security
- [ ] No hardcoded secrets in code
- [ ] SQL injection prevention verified
- [ ] CORS properly configured
- [ ] Rate limiting enabled
- [ ] HTTPS enforced (Render auto-provisions SSL)
- [ ] Database user has minimal permissions

## Monitoring & Alerts
- [ ] Error logging configured
- [ ] Monitoring dashboard set up (optional: Sentry, DataDog)
- [ ] Alerts configured (email, Slack)
- [ ] Health check endpoint working
- [ ] Logs accessible and rotated

## Final Steps
- [ ] Create feature branch for deployment
- [ ] Create Pull Request with changelog
- [ ] Get code review approval
- [ ] Deploy to staging first (if available)
- [ ] Load test on staging
- [ ] Merge to main
- [ ] Monitor first deployment
- [ ] Document any issues

## Post-Deployment
- [ ] Verify all services running on Render
- [ ] Test critical workflows
- [ ] Check database integrity
- [ ] Monitor logs for errors
- [ ] Verify backups configured
- [ ] Update status page (if applicable)
- [ ] Notify stakeholders

## Rollback Plan
- [ ] Previous image available: `docker pull ghcr.io/your-org/your-repo:previous-tag`
- [ ] Database backup exists
- [ ] Restore procedure documented
- [ ] Tested rollback process

## Performance Targets
- [ ] API response time < 200ms
- [ ] Database queries optimized
- [ ] No memory leaks seen in logs
- [ ] CPU usage < 75%
