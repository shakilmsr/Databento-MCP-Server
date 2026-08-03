import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone
import databento_core as core

def test_session_info():
    client = core.DatabentoClient(api_key="db-test")
    dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    info = client.get_session_info(dt)
    assert info["currentSession"] == "London"
    assert info["sessionStart"].endswith("07:00:00+00:00")
    assert info["sessionEnd"].endswith("14:00:00+00:00")

def test_parse_csv():
    client = core.DatabentoClient(api_key="db-test")
    csv = "col1,col2\nval1,val2\nval3,val4"
    res = client.parse_csv(csv)
    assert len(res) == 2
    assert res[0]["col1"] == "val1"
    assert res[1]["col2"] == "val4"

@pytest.mark.asyncio
async def test_get_futures_quote_live():
    client = core.DatabentoClient(api_key="db-test")
    with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
        # Mocking a CSV response with one row
        mock_get.return_value = "ts_recv,ts_event,bid_px_00,ask_px_00\n1000,1000,4500000000000,4501000000000"
        
        quote = await client.get_futures_quote("ES")
        assert quote["symbol"] == "ES"
        assert quote["bid"] == 4500.0
        assert quote["ask"] == 4501.0
        assert quote["price"] == 4500.5
