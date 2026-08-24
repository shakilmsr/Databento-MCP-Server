"""
databento-mcp-server — FastMCP server for Databento market data.
"""

import os
from datetime import datetime
from typing import Optional, List
from fastmcp import FastMCP
import databento_core as core

mcp = FastMCP("databento")

@mcp.tool()
async def get_futures_quote(symbol: str) -> dict:
    """Get current price quote for ES or NQ futures contracts."""
    client = core.get_client()
    return await client.get_futures_quote(symbol)

@mcp.tool()
def get_session_info(timestamp: Optional[str] = None) -> dict:
    """Get current trading session information (Asian/London/NY)."""
    dt = datetime.fromisoformat(timestamp) if timestamp else None
    client = core.get_client()
    return client.get_session_info(dt)

@mcp.tool()
async def get_historical_bars(symbol: str, timeframe: str, count: int) -> list:
    """Get historical OHLCV bars for futures contracts."""
    client = core.get_client()
    return await client.get_historical_bars(symbol, timeframe, count)

@mcp.tool()
async def symbology_resolve(dataset: str, symbols: List[str], stype_in: str, stype_out: str, start_date: str, end_date: Optional[str] = None) -> dict:
    """Resolve symbols to instrument IDs or other symbol types across a date range."""
    client = core.get_client()
    return await client.symbology_resolve(dataset, symbols, stype_in, stype_out, start_date, end_date)

@mcp.tool()
async def timeseries_get_range(dataset: str, symbols: str, schema: str, start: str, end: Optional[str] = None, stype_in: Optional[str] = None, stype_out: Optional[str] = None, limit: Optional[int] = None) -> list:
    """Get historical market data with flexible schemas and date ranges."""
    params = {
        "dataset": dataset,
        "symbols": symbols,
        "schema": schema,
        "start": start
    }
    if end: params["end"] = end
    if stype_in: params["stype_in"] = stype_in
    if stype_out: params["stype_out"] = stype_out
    if limit: params["limit"] = limit
    
    client = core.get_client()
    return await client.timeseries_get_range(params)

@mcp.tool()
async def metadata_list_datasets(start_date: Optional[str] = None, end_date: Optional[str] = None) -> list:
    """List all available Databento datasets with optional date range filtering."""
    client = core.get_client()
    return await client.metadata_list_datasets(start_date, end_date)

@mcp.tool()
async def metadata_list_schemas(dataset: str) -> list:
    """List available data schemas for a specific dataset."""
    client = core.get_client()
    return await client.metadata_list_schemas(dataset)

@mcp.tool()
async def metadata_list_publishers(dataset: Optional[str] = None) -> list:
    """List publishers with their details, optionally filtered by dataset."""
    client = core.get_client()
    return await client.metadata_list_publishers(dataset)

@mcp.tool()
async def metadata_list_fields(schema: str, encoding: Optional[str] = None) -> list:
    """List fields available for a specific schema with their types and descriptions."""
    client = core.get_client()
    return await client.metadata_list_fields(schema, encoding)

@mcp.tool()
async def metadata_get_cost(dataset: str, symbols: str, schema: str, start: str, end: Optional[str] = None, mode: Optional[str] = None, stype_in: Optional[str] = None, stype_out: Optional[str] = None) -> dict:
    """Calculate the cost in USD for a historical data query before downloading."""
    params = {
        "dataset": dataset,
        "symbols": symbols,
        "schema": schema,
        "start": start
    }
    if end: params["end"] = end
    if mode: params["mode"] = mode
    if stype_in: params["stype_in"] = stype_in
    if stype_out: params["stype_out"] = stype_out
    
    client = core.get_client()
    return await client.metadata_get_cost(params)

@mcp.tool()
async def metadata_get_dataset_range(dataset: str) -> dict:
    """Get the available date range for a dataset."""
    client = core.get_client()
    return await client.metadata_get_dataset_range(dataset)

@mcp.tool()
async def batch_submit_job(dataset: str, symbols: List[str], schema: str, start: str, end: Optional[str] = None, encoding: Optional[str] = None, compression: Optional[str] = None, stype_in: Optional[str] = None, stype_out: Optional[str] = None, split_duration: Optional[str] = None, split_size: Optional[int] = None, split_symbols: Optional[bool] = None, limit: Optional[int] = None) -> dict:
    """Submit a batch data download job for large historical datasets. Returns job ID and status."""
    params = {
        "dataset": dataset,
        "symbols": symbols,
        "schema": schema,
        "start": start
    }
    if end: params["end"] = end
    if encoding: params["encoding"] = encoding
    if compression: params["compression"] = compression
    if stype_in: params["stype_in"] = stype_in
    if stype_out: params["stype_out"] = stype_out
    if split_duration: params["split_duration"] = split_duration
    if split_size: params["split_size"] = split_size
    if split_symbols is not None: params["split_symbols"] = split_symbols
    if limit: params["limit"] = limit
    
    client = core.get_client()
    return await client.batch_submit_job(params)

@mcp.tool()
async def batch_list_jobs(states: Optional[List[str]] = None, since: Optional[str] = None) -> list:
    """List all batch jobs with their current status."""
    client = core.get_client()
    return await client.batch_list_jobs(states, since)

if __name__ == "__main__":
    port = int(os.environ.get("MCP_PORT", "8008"))
    print(f"Starting databento MCP server on port {port}...")
    mcp.run(transport="http", host="0.0.0.0", port=port)
