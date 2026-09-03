import pytest
from sec_scraper.client import EdgarClient, FixtureTransportAdapter, HttpTransportAdapter


def test_resolve_cik_known_ticker():
    adapter = FixtureTransportAdapter()
    client = EdgarClient(transport=adapter)

    cik, display_name = client.resolve_cik("TSLA")
    assert cik == "0001318605"
    assert display_name == "TSLA"


def test_resolve_cik_numeric_string():
    adapter = FixtureTransportAdapter()
    client = EdgarClient(transport=adapter)

    cik, display_name = client.resolve_cik("320193")
    assert cik == "0000320193"
    assert display_name == "320193"


def test_resolve_cik_via_sec_company_tickers_directory():
    mock_directory = {
        "0": {"cik_str": 789019, "ticker": "MSFT", "title": "MICROSOFT CORP"},
        "1": {"cik_str": 1045810, "ticker": "NVDA", "title": "NVIDIA CORP"},
        "2": {"cik_str": 999999, "ticker": "CUSTOM", "title": "Custom Corp"},
    }
    adapter = FixtureTransportAdapter(fixtures={
        "https://www.sec.gov/files/company_tickers.json": mock_directory
    })
    client = EdgarClient(transport=adapter)

    cik, display_name = client.resolve_cik("CUSTOM")
    assert cik == "0000999999"
    assert display_name == "Custom Corp"


def test_resolve_cik_raises_for_unknown():
    adapter = FixtureTransportAdapter(fixtures={
        "https://www.sec.gov/files/company_tickers.json": {}
    })
    client = EdgarClient(transport=adapter)

    with pytest.raises(ValueError, match="Could not resolve CIK for symbol"):
        client.resolve_cik("UNKNOWN")


def test_get_company_facts_uses_transport_seam():
    mock_facts = {
        "cik": 1318605,
        "entityName": "Tesla, Inc.",
        "facts": {}
    }
    adapter = FixtureTransportAdapter(fixtures={
        "https://data.sec.gov/api/xbrl/companyfacts/CIK0001318605.json": mock_facts
    })
    client = EdgarClient(transport=adapter)

    facts = client.get_company_facts("TSLA")
    assert facts["entityName"] == "Tesla, Inc."
    assert facts["cik"] == 1318605
    assert len(adapter.calls) == 1
    assert "CIK0001318605.json" in adapter.calls[0]["url"]
    assert "User-Agent" in adapter.calls[0]["headers"]
