# CI/CD Pipeline

This document describes the CI/CD pipeline for the Odoo MCP Server.

## Overview

```
PR Created → CI Checks → Automerge → Deploy to Staging
                                          ↓
                                   (manual) Deploy to Production
```

## Workflows

### 1. CI Workflow (`.github/workflows/ci.yml`)

Triggered on:
- Push to `main`
- Pull requests to `main`

**Jobs:**

| Job | Description | Dependencies |
|-----|-------------|--------------|
| `lint` | Runs `ruff check` and `mypy` type checking | None |
| `unit-tests` | Runs `pytest tests/unit` with coverage | None |
| `integration-tests` | Runs `pytest tests/integration` | Only on `main` or with `run-integration` label |
| `build` | Builds Docker image | `lint`, `unit-tests` |
| `deploy-staging` | Deploys to Cloud Run staging | `build`, `integration-tests` (only on `main`) |

### 2. Automerge Workflow (`.github/workflows/automerge.yml`)

Triggered when:
- CI workflow completes successfully on a PR branch

**Behavior:**
- Automatically merges PRs when all CI checks pass
- Uses **squash merge** to keep history clean
- Commit message uses the PR title
- Retries up to 6 times if merge fails (e.g., due to branch protection)

## Development Workflow

### Creating a PR

```bash
# Create feature branch
git checkout -b feature/my-feature

# Make changes and commit
git add .
git commit -m "feat: Add my feature"

# Push and create PR
git push -u origin feature/my-feature
gh pr create --title "feat: Add my feature" --body "Description"
```

### What Happens After PR Creation

1. **CI runs** - lint, tests, build
2. **Automerge triggers** - when CI passes, PR is automatically merged
3. **Deploy to staging** - merge to `main` triggers staging deployment

### Skipping Automerge

To prevent automerge, add the `no-automerge` label to your PR.

## Environments

### Staging

- **Service:** `odoo-mcp-server` (Cloud Run)
- **Region:** `europe-west1`
- **URL:** `https://odoo-mcp-server-{PROJECT_NUMBER}.europe-west1.run.app`
- **Deployed:** Automatically on merge to `main`

### Production

- **Status:** Not yet configured
- **Deployment:** Manual approval required in GitHub Actions

## Secrets Configuration

### GitHub Secrets

| Secret | Description |
|--------|-------------|
| `GCP_PROJECT_ID` | GCP project ID (`odoo-crm-461310`) |
| `GCP_SA_KEY` | Service account JSON key for GCP |
| `STAGING_ODOO_URL` | Odoo staging instance URL |
| `STAGING_ODOO_DB` | Odoo staging database name |
| `OAUTH_CLIENT_ID` | Google OAuth client ID |
| `OAUTH_CLIENT_SECRET` | Google OAuth client secret |

### GCP Secrets (Secret Manager)

| Secret | Description |
|--------|-------------|
| `odoo-api-key` | Odoo API key for service account |
| `oauth-client-secret` | Google OAuth client secret |

## Troubleshooting

### CI Failing

1. Check the failed job in GitHub Actions
2. Common issues:
   - `lint` - Run `ruff check .` locally to fix
   - `mypy` - Run `mypy src/ --ignore-missing-imports` locally
   - `unit-tests` - Run `pytest tests/unit -v` locally

### Automerge Not Working

1. Ensure CI has passed (green checkmark)
2. Check if `no-automerge` label is present
3. Verify GitHub token has write permissions
4. Check automerge workflow logs for errors

### Deployment Not Triggering

1. Automerge must complete first
2. Check if merge happened to `main` branch
3. Review `deploy-staging` job logs in GitHub Actions

## Manual Operations

### Force Deploy (Emergency Only)

```bash
# Only use if CI/CD is broken
gcloud run deploy odoo-mcp-server \
  --image gcr.io/odoo-crm-461310/odoo-mcp-server:latest \
  --region europe-west1
```

### Check Deployment Status

```bash
# Health check
curl https://odoo-mcp-server-574793647362.europe-west1.run.app/health

# View logs
gcloud run logs read odoo-mcp-server --region=europe-west1 --limit=50
```
