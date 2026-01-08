# Keboola Odoo MCP Server

A Model Context Protocol (MCP) server that enables AI assistants like Claude to securely interact with Keboola's Odoo 18 ERP instance using OAuth 2.1 authentication.

## Features

- **OAuth 2.1 Authentication**: Secure multi-user access with PKCE and token refresh
- **Full CRUD Operations**: Search, create, update, and delete Odoo records
- **Model Discovery**: List and inspect available Odoo models
- **Permission-Aware**: Respects Odoo's access control rules
- **Claude & Slack Integration**: Works with Claude Desktop and Slack bots
- **Production Ready**: Docker support, CI/CD, and Cloud Run deployment

## Quick Start

### Prerequisites

- Python 3.12+
- Access to Odoo 18 instance
- OAuth 2.1 Authorization Server (Auth0, Google Identity, etc.)

### Installation

```bash
# Clone the repository
git clone https://github.com/keboola/odoo-mcp-server.git
cd odoo-mcp-server

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"
```

### Configuration

Create a `.env` file:

```bash
# Odoo Connection
ODOO_URL=https://erp.internel.keboola.com
ODOO_DB=keboola
ODOO_API_KEY=your_api_key_here

# OAuth Configuration
OAUTH_AUTHORIZATION_SERVER=https://auth.keboola.com
OAUTH_RESOURCE_IDENTIFIER=https://odoo-mcp.keboola.com

# Server Settings
HTTP_HOST=0.0.0.0
HTTP_PORT=8080
```

### Running the Server

```bash
# HTTP server (for remote MCP)
python -m odoo_mcp_server.http_server

# Or using stdio (for local MCP clients)
python -m odoo_mcp_server.server
```

## Claude Desktop Integration

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "keboola-odoo": {
      "url": "https://your-deployment-url/mcp",
      "transport": "streamable-http",
      "oauth": {
        "client_id": "claude-desktop",
        "authorization_server": "https://auth.keboola.com",
        "scopes": ["openid", "odoo.read", "odoo.write"]
      }
    }
  }
}
```

## Available Tools

| Tool | Description |
|------|-------------|
| `search_records` | Search for records with domain filters |
| `get_record` | Get a single record by ID |
| `create_record` | Create a new record |
| `update_record` | Update an existing record |
| `delete_record` | Delete a record |
| `count_records` | Count records matching criteria |
| `list_models` | List available Odoo models |

## Testing

```bash
# Run all automated tests
pytest

# Run specific test categories
pytest -m unit          # Unit tests
pytest -m integration   # Integration tests
pytest -m oauth         # OAuth tests

# Run with coverage
pytest --cov=src/ --cov-report=html
```

### E2E Tests (Claude Code Chrome Integration)

E2E tests use Claude Code's Chrome integration for browser automation:

```bash
# Run interactive E2E test suite
./scripts/run_e2e_tests.sh

# Or manually with Claude Code
claude --chrome
# Then use /chrome to verify connection
```

See [tests/e2e/README.md](tests/e2e/README.md) for detailed E2E testing guide.

## Development

See [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) for the complete development guide, architecture details, and sprint plans.

### Project Structure

```
odoo-mcp-server/
├── src/odoo_mcp_server/
│   ├── server.py          # Main MCP server
│   ├── http_server.py     # HTTP transport with OAuth
│   ├── config.py          # Configuration management
│   ├── oauth/             # OAuth 2.1 Resource Server
│   ├── odoo/              # Odoo XML-RPC client
│   ├── tools/             # MCP tools implementation
│   └── resources/         # MCP resources
├── tests/
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── e2e/               # Playwright E2E tests
├── docker/                # Docker configuration
└── config/                # Configuration examples
```

## Deployment

### Docker

```bash
# Build
docker build -t keboola/odoo-mcp-server -f docker/Dockerfile .

# Run
docker run -p 8080:8080 \
  -e ODOO_URL=https://erp.internel.keboola.com \
  -e ODOO_API_KEY=your_key \
  keboola/odoo-mcp-server
```

### Google Cloud Run

```bash
gcloud run deploy odoo-mcp-server \
  --image gcr.io/your-project/odoo-mcp-server \
  --region europe-west1 \
  --allow-unauthenticated
```

## Security

- OAuth 2.1 with PKCE for all authentication flows
- Token validation against JWKS
- User-scoped Odoo permissions
- No credential storage (stateless)

## License

MIT License - see [LICENSE](LICENSE) for details.
