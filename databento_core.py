import os
import json
import asyncio
import httpx
from datetime import datetime, timedelta, timezone

DATASET = "GLBX.MDP3"
LIVE_BASE_URL = "https://live.databento.com"
HIST_BASE_URL = "https://hist.databento.com"

SYMBOL_MAP = {
    "ES": "ES.c.0",
    "NQ": "NQ.c.0",
}

class DatabentoClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("DATABENTO_API_KEY")
        if not self.api_key:
            raise ValueError("DATABENTO_API_KEY is required")
        if not self.api_key.startswith("db-"):
            raise ValueError("DATABENTO_API_KEY must start with 'db-'")
        
        self.auth = (self.api_key, "")
        self.hist_client = httpx.AsyncClient(base_url=HIST_BASE_URL, auth=self.auth, timeout=30.0)
        self.live_client = httpx.AsyncClient(base_url=LIVE_BASE_URL, auth=self.auth, timeout=30.0)
        
        # Simple cache for quotes
        self._quote_cache = {}

    async def get(self, endpoint: str, params: dict = None, use_live: bool = False):
        client = self.live_client if use_live else self.hist_client
        clean_params = {k: v for k, v in params.items() if v is not None} if params else None
        
        response = await client.get(endpoint, params=clean_params)
        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}: {response.text}")
        return response.text

    async def post_form(self, endpoint: str, data: dict):
        clean_data = {}
        for k, v in data.items():
            if v is not None:
                if isinstance(v, list):
                    clean_data[k] = ",".join(str(x) for x in v)
                elif isinstance(v, bool):
                    clean_data[k] = "true" if v else "false"
                else:
                    clean_data[k] = str(v)
                    
        response = await self.hist_client.post(endpoint, data=clean_data)
        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}: {response.text}")
        return response.text

    def parse_csv(self, csv_text: str) -> list[dict]:
        lines = [line.strip() for line in csv_text.strip().split("\n") if line.strip()]
        if not lines:
            return []
        
        headers = lines[0].split(",")
        result = []
        for line in lines[1:]:
            values = line.split(",")
            row = {headers[i].strip(): values[i].strip() if i < len(values) else "" for i in range(len(headers))}
            result.append(row)
        return result

    def get_session_info(self, dt: datetime = None) -> dict:
        dt = dt or datetime.now(timezone.utc)
        utc_hour = dt.hour
        
        if 0 <= utc_hour < 7:
            current_session = "Asian"
            start_hour, end_hour = 0, 7
        elif 7 <= utc_hour < 14:
            current_session = "London"
            start_hour, end_hour = 7, 14
        elif 14 <= utc_hour < 22:
            current_session = "NY"
            start_hour, end_hour = 14, 22
        else:
            current_session = "Unknown"
            start_hour, end_hour = utc_hour, utc_hour
            
        session_start = dt.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        session_end = dt.replace(hour=end_hour, minute=0, second=0, microsecond=0)
        
        return {
            "currentSession": current_session,
            "sessionStart": session_start.isoformat(),
            "sessionEnd": session_end.isoformat(),
            "timestamp": dt.isoformat()
        }

    async def get_futures_quote(self, symbol: str) -> dict:
        if symbol not in SYMBOL_MAP:
            raise ValueError(f"Invalid symbol: {symbol}")
            
        # Cache check (30s)
        now = datetime.now(timezone.utc).timestamp()
        if symbol in self._quote_cache:
            cache_entry = self._quote_cache[symbol]
            if now - cache_entry["timestamp"] < 30:
                return cache_entry["data"]

        db_symbol = SYMBOL_MAP[symbol]
        session_info = self.get_session_info()
        use_live = session_info["currentSession"] == "NY"
        
        today = datetime.now(timezone.utc)
        start_date = today - timedelta(days=7)
        
        params = {
            "dataset": DATASET,
            "symbols": db_symbol,
            "stype_in": "continuous",
            "stype_out": "instrument_id",
            "start": start_date.strftime("%Y-%m-%d"),
            "end": today.strftime("%Y-%m-%d"),
            "schema": "mbp-1",
            "limit": 100
        }
        
        response_text = None
        if use_live:
            try:
                live_text = await self.get("/v0/timeseries.get_range", params, use_live=True)
                if len(live_text.strip().split("\n")) > 1:
                    response_text = live_text
            except Exception:
                pass
                
        if not response_text:
            response_text = await self.get("/v0/timeseries.get_range", params, use_live=False)
            
        rows = self.parse_csv(response_text)
        if not rows:
            raise Exception(f"No quote data available for {symbol}")
            
        latest = rows[-1]
        
        try:
            bid_px = float(latest.get("bid_px_00", 0)) / 1e9
            ask_px = float(latest.get("ask_px_00", 0)) / 1e9
            ts_event = int(latest.get("ts_event", 0))
            
            price = (bid_px + ask_px) / 2
            timestamp = ts_event / 1_000_000_000
            data_age_ms = int((now - timestamp) * 1000)
            
            data = {
                "symbol": symbol,
                "price": price,
                "bid": bid_px,
                "ask": ask_px,
                "timestamp": datetime.fromtimestamp(timestamp, timezone.utc).isoformat(),
                "dataAge": data_age_ms
            }
            
            self._quote_cache[symbol] = {"data": data, "timestamp": now}
            return data
        except (ValueError, KeyError) as e:
            raise Exception(f"Failed to parse quote row: {e}")

    async def get_historical_bars(self, symbol: str, timeframe: str, count: int) -> list:
        if symbol not in SYMBOL_MAP:
            raise ValueError(f"Invalid symbol: {symbol}")
            
        db_symbol = SYMBOL_MAP[symbol]
        today = datetime.now(timezone.utc)
        
        if timeframe == "1h":
            start_date = today - timedelta(days=int(count / 24) + 7)
            schema = "ohlcv-1h"
        elif timeframe == "H4":
            start_date = today - timedelta(days=int(count / 6) + 7)
            schema = "ohlcv-1h"
        elif timeframe == "1d":
            start_date = today - timedelta(days=count + 7)
            schema = "ohlcv-1d"
        else:
            raise ValueError("Timeframe must be 1h, H4, or 1d")
            
        params = {
            "dataset": DATASET,
            "symbols": db_symbol,
            "stype_in": "continuous",
            "stype_out": "instrument_id",
            "start": start_date.strftime("%Y-%m-%d"),
            "end": today.strftime("%Y-%m-%d"),
            "schema": schema,
            "limit": 1000
        }
        
        response_text = await self.get("/v0/timeseries.get_range", params, use_live=False)
        rows = self.parse_csv(response_text)
        
        bars = []
        for r in rows:
            try:
                bars.append({
                    "timestamp": datetime.fromtimestamp(int(r["ts_event"]) / 1e9, timezone.utc).isoformat(),
                    "open": float(r["open"]) / 1e9,
                    "high": float(r["high"]) / 1e9,
                    "low": float(r["low"]) / 1e9,
                    "close": float(r["close"]) / 1e9,
                    "volume": float(r["volume"])
                })
            except (ValueError, KeyError):
                continue
                
        if not bars:
            raise Exception(f"No bar data available for {symbol}")
            
        if timeframe == "H4":
            h4_bars = []
            for i in range(0, len(bars), 4):
                chunk = bars[i:i+4]
                if not chunk: continue
                h4_bars.append({
                    "timestamp": chunk[0]["timestamp"],
                    "open": chunk[0]["open"],
                    "high": max(b["high"] for b in chunk),
                    "low": min(b["low"] for b in chunk),
                    "close": chunk[-1]["close"],
                    "volume": sum(b["volume"] for b in chunk)
                })
            bars = h4_bars
            
        return bars[-count:]

    async def symbology_resolve(self, dataset: str, symbols: list[str], stype_in: str, stype_out: str, start_date: str, end_date: str = None) -> dict:
        params = {
            "dataset": dataset,
            "symbols": ",".join(symbols),
            "stype_in": stype_in,
            "stype_out": stype_out,
            "start_date": start_date,
        }
        if end_date:
            params["end_date"] = end_date
            
        resp = await self.get("/v0/symbology.resolve", params)
        return json.loads(resp)
        
    async def timeseries_get_range(self, params: dict) -> list[dict]:
        resp = await self.get("/v0/timeseries.get_range", params)
        return self.parse_csv(resp)
        
    async def batch_submit_job(self, params: dict) -> dict:
        resp = await self.post_form("/v0/batch.submit_job", params)
        return json.loads(resp)
        
    async def batch_list_jobs(self, states: list[str] = None, since: str = None) -> list[dict]:
        params = {}
        if states: params["states"] = ",".join(states)
        if since: params["since"] = since
        resp = await self.get("/v0/batch.list_jobs", params)
        return json.loads(resp)

    async def metadata_list_datasets(self, start_date: str = None, end_date: str = None) -> list:
        params = {}
        if start_date: params["start_date"] = start_date
        if end_date: params["end_date"] = end_date
        resp = await self.get("/v0/metadata.list_datasets", params)
        return json.loads(resp)
        
    async def metadata_list_schemas(self, dataset: str) -> list:
        resp = await self.get("/v0/metadata.list_schemas", {"dataset": dataset})
        return json.loads(resp)
        
    async def metadata_list_publishers(self, dataset: str = None) -> list:
        params = {"dataset": dataset} if dataset else {}
        resp = await self.get("/v0/metadata.list_publishers", params)
        return json.loads(resp)
        
    async def metadata_list_fields(self, schema: str, encoding: str = None) -> list:
        params = {"schema": schema}
        if encoding: params["encoding"] = encoding
        resp = await self.get("/v0/metadata.list_fields", params)
        return json.loads(resp)
        
    async def metadata_get_cost(self, params: dict) -> dict:
        resp = await self.get("/v0/metadata.get_cost", params)
        return json.loads(resp)
        
    async def metadata_get_dataset_range(self, dataset: str) -> dict:
        resp = await self.get("/v0/metadata.get_dataset_range", {"dataset": dataset})
        return json.loads(resp)

# Global singleton
_client = None

def get_client() -> DatabentoClient:
    global _client
    if _client is None:
        _client = DatabentoClient()
    return _client
