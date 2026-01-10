# Keboola Odoo MCP Server

A Model Context Protocol (MCP) server that enables AI assistants like Claude to securely interact with Keboola's Odoo 18 ERP instance.

## Development Workflow

### Branching & PRs
1. Create a feature/fix branch from `main`
2. Make changes and commit
3. Push branch and create PR
4. Merge PR (squash preferred)

### Deployment
**IMPORTANT: Do NOT deploy manually with gcloud commands.**

Deployments are handled automatically by GitHub CI:
- Merging to `main` triggers automatic deployment to staging
- Production deployments require manual approval in GitHub Actions

### Testing
```bash
# Unit tests
pytest tests/unit/ -v

# Type checking
mypy src/

# All tests
pytest
```

## Project Structure

```
odoo-mcp-server/
├── src/odoo_mcp_server/
│   ├── server.py          # Main MCP server
│   ├── http_server.py     # HTTP transport
│   ├── config.py          # Configuration
│   ├── odoo/              # Odoo XML-RPC client
│   └── tools/             # MCP tools (employee.py, etc.)
├── tests/
│   ├── unit/              # Unit tests
│   └── e2e/               # E2E tests
├── docker/                # Docker config (production)
└── Dockerfile             # Root Dockerfile (Cloud Run)
```

## Key Files

- `src/odoo_mcp_server/tools/employee.py` - Employee self-service tools (leave balance, requests, etc.)
- `src/odoo_mcp_server/odoo/client.py` - Odoo XML-RPC client wrapper

## Environments

### Staging (Current)
- **MCP URL:** https://odoo-mcp-server-55974118220.europe-west1.run.app/mcp
- **Health:** https://odoo-mcp-server-55974118220.europe-west1.run.app/health
- **Cloud Run Service:** `odoo-mcp-server` (europe-west1)
- **Connected to:** Staging Odoo instance
- **Deployed by:** GitHub CI on merge to `main`

### Production (Future)
- **URL:** Will be on `keboola.com` domain
- **Status:** Not yet configured
- **Deployment:** Separate process (TBD)

## Deployment Notes

1. **GitHub CI deploys to staging automatically** on merge to `main`
2. **Never deploy manually** - let CI handle it
3. **Check health endpoint** to verify deployment: `/health` returns `code_version`
4. **E2E tests** must pass before promoting to production
