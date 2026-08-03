# DataBento MCP Server

Professional market data access via DataBento API, implemented as a Python FastMCP server.

## What's New

**Version 4.0 - Python FastMCP Rewrite**

This project has been completely rewritten in Python using `FastMCP` to align with standard AI orchestration environments. 
The TypeScript/Node.js implementation has been removed in favor of this streamlined Python stack.

### Features

- 🎯 **Real-time Futures Quotes** - Current prices for ES and NQ contracts
- 📊 **Historical Timeseries** - Stream any market data schema across date ranges
- 📈 **Batch Downloads** - Submit and manage large historical data jobs
- 🔍 **Symbol Resolution** - Resolve symbols to instrument IDs across datasets
- 📚 **Metadata Discovery** - Explore datasets, schemas, fields, and pricing
- ⏰ **Session Detection** - Automatic Asian/London/NY session identification
- 🚀 **Built-in FastMCP** - Easily connects via Server-Sent Events (SSE) or Standard IO

## Installation & Setup

### Prerequisites

- Python 3.12+
- `uv` (recommended) or `pip`
- DataBento API key ([get one here](https://databento.com))

### Environment Setup

1. Clone or download this repository:
```bash
git clone https://github.com/shakilmsr/databento-mcp-server
cd databento-mcp-server
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file or export your API key in your environment:
```bash
DATABENTO_API_KEY=db-your-api-key-here
MCP_PORT=8008  # Optional, defaults to 8008
```

## Running the Server

### Option 1: Standalone SSE Server (Recommended)
You can run the server directly, exposing the FastMCP HTTP/SSE endpoints:
```bash
python server.py
```
This will start the server on `http://0.0.0.0:8008` (or the port specified in `MCP_PORT`).

### Option 2: Docker Compose
A `docker-compose.yml` is provided for containerized deployments:
```bash
docker compose up -d --build
```

### Option 3: Claude Desktop (Standard IO)
Add the following to your `claude_desktop` config:
```json
{
  "mcpServers": {
    "databento": {
      "command": "python",
      "args": ["/path/to/databento-mcp-server/server.py"],
      "env": {
        "DATABENTO_API_KEY": "db-your-api-key-here"
      }
    }
  }
}
```

## Available Tools

The MCP server provides 14 tools organized into categories:

| Category | Tools | Description |
|----------|-------|-------------|
| **Original** | 3 tools | ES/NQ futures quotes, session info, historical bars |
| **Timeseries** | 1 tool | Historical market data streaming with flexible schemas |
| **Symbology** | 1 tool | Symbol resolution and conversion |
| **Metadata** | 6 tools | Dataset discovery, schema info, cost estimation |
| **Batch** | 2 tools | Large-scale data download job management (`batch_submit_job`, `batch_list_jobs`) |

*Note: For detailed inputs/outputs, refer to the individual tool descriptions exposed by the MCP server.*
