"""BrokerFlow date alignment, share units, and daily drill-down contract."""

from datetime import date

from fastapi.testclient import TestClient

from src.backend.tests.conftest import Harness


def test_five_day_chart_and_daily_broker_popup(
    client: TestClient, harness: Harness
) -> None:
    original = harness.transport._get_broker_summary

    def with_lots(start: str, end: str) -> dict:
        payload = original(start, end)
        for day in payload["data"]:
            for broker in day["summary"]:
                if broker["broker_code"] == "B0":
                    broker["blot"] = 90
                    broker["slot"] = 10
                    broker["nlot"] = 80
                elif broker["broker_code"] == "S0":
                    broker["blot"] = 5
                    broker["slot"] = 75
                    broker["nlot"] = -70
        return payload

    harness.transport._get_broker_summary = with_lots
    response = client.get("/api/v1/stocks/TEST/broker-flow?range=5d")
    assert response.status_code == 200, response.text
    body = response.json()
    expected_dates = [day.isoformat() for day in harness.transport.days[-5:]]
    assert body["range"] == "5d"
    assert [row["date"] for row in body["prices"]] == expected_dates
    assert [row["date"] for row in body["days"]] == expected_dates
    assert body["top_buyers"][0]["broker_code"] == "B0"
    assert body["top_sellers"][0]["broker_code"] == "S0"
    buyer = next(row for row in body["broker_series"] if row["broker_code"] == "B0")
    seller = next(row for row in body["broker_series"] if row["broker_code"] == "S0")
    assert [point["cumulative_net_shares"] for point in buyer["points"]] == [
        8000,
        16000,
        24000,
        32000,
        40000,
    ]
    assert seller["points"][-1]["cumulative_net_shares"] == -35000
    assert body["days"][-1]["top_buyers"][0] == {
        "broker_code": "B0",
        "shares": 8000,
    }
    assert body["days"][-1]["top_sellers"][0] == {
        "broker_code": "S0",
        "shares": 7000,
    }


def test_three_month_broker_activity_uses_provider_safe_chunks(
    client: TestClient, harness: Harness
) -> None:
    original = harness.transport._get_broker_summary
    windows: list[tuple[str, str]] = []

    def tracking_chunks(start: str, end: str) -> dict:
        windows.append((start, end))
        return original(start, end)

    harness.transport._get_broker_summary = tracking_chunks
    response = client.get("/api/v1/stocks/TEST/broker-flow?range=3m")
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(windows) > 1
    assert all(
        (date.fromisoformat(end) - date.fromisoformat(start)).days <= 13
        for start, end in windows
    )
    assert len(body["days"]) == len(body["prices"])
    assert body["effective_start"] == body["prices"][0]["date"]
    assert body["effective_end"] == body["prices"][-1]["date"]
    assert len(body["prices"]) == 60


def test_one_month_uses_last_twenty_observed_trading_sessions(
    client: TestClient, harness: Harness
) -> None:
    response = client.get("/api/v1/stocks/TEST/broker-flow?range=1m")
    assert response.status_code == 200, response.text
    body = response.json()
    assert [row["date"] for row in body["prices"]] == [
        day.isoformat() for day in harness.transport.days[-20:]
    ]
    assert body["effective_end"] == harness.transport.days[-1].isoformat()
    assert body["incomplete_history"] is False


def test_unplottable_price_dates_do_not_extend_broker_lines(
    client: TestClient, harness: Harness
) -> None:
    # A dated provider row can have no traded candle; daily broker rows must
    # not create a phantom line continuation on those dates.
    harness.transport.rows[-2]["open"] = None
    harness.transport.rows[-2]["high"] = None
    harness.transport.rows[-2]["low"] = None
    harness.transport.rows[-1]["volume"] = 0
    expected = [day.isoformat() for day in harness.transport.days[-7:-2]]
    ranking_windows: list[tuple[str, str]] = []
    broker_windows: list[tuple[str, str]] = []
    original_top = harness.transport._get_top_brokers
    original_summary = harness.transport._get_broker_summary

    def track_top(start: str, end: str, **params: object) -> dict:
        ranking_windows.append((start, end))
        return original_top(start, end, **params)

    def track_summary(start: str, end: str) -> dict:
        broker_windows.append((start, end))
        return original_summary(start, end)

    harness.transport._get_top_brokers = track_top
    harness.transport._get_broker_summary = track_summary
    response = client.get("/api/v1/stocks/TEST/broker-flow?range=5d")
    assert response.status_code == 200, response.text
    body = response.json()
    assert [row["date"] for row in body["prices"]] == expected
    assert [row["date"] for row in body["days"]] == expected
    assert body["excluded_price_dates"] == [
        day.isoformat() for day in harness.transport.days[-2:]
    ]
    assert body["effective_end"] == expected[-1]
    assert ranking_windows == [(expected[0], expected[-1])]
    assert broker_windows[-1][1] == expected[-1]
    assert all(
        point["date"] in expected
        for series in body["broker_series"]
        for point in series["points"]
    )


def test_broker_absent_from_reported_day_has_zero_activity(
    client: TestClient, harness: Harness
) -> None:
    original = harness.transport._get_broker_summary
    missing_date = harness.transport.days[-3].isoformat()

    def with_gap(start: str, end: str) -> dict:
        payload = original(start, end)
        for day in payload["data"]:
            if day["date"] == missing_date:
                day["summary"] = [
                    broker for broker in day["summary"] if broker["broker_code"] != "B0"
                ]
        return payload

    harness.transport._get_broker_summary = with_gap
    response = client.get("/api/v1/stocks/TEST/broker-flow?range=5d")
    assert response.status_code == 200, response.text
    body = response.json()
    buyer = next(row for row in body["broker_series"] if row["broker_code"] == "B0")
    assert body["status"] == "complete"
    assert buyer["points"][2]["net_shares"] == 0
    assert buyer["points"][2]["cumulative_net_shares"] == 0
    assert buyer["points"][3]["cumulative_net_shares"] == 0


def test_missing_whole_day_is_gap_but_later_broker_data_returns(
    client: TestClient, harness: Harness
) -> None:
    original = harness.transport._get_broker_summary
    missing_date = harness.transport.days[-3].isoformat()

    def with_gap(start: str, end: str) -> dict:
        payload = original(start, end)
        payload["data"] = [
            day for day in payload["data"] if day["date"] != missing_date
        ]
        for day in payload["data"]:
            next(broker for broker in day["summary"] if broker["broker_code"] == "B0")[
                "nlot"
            ] = 8
        return payload

    harness.transport._get_broker_summary = with_gap
    response = client.get("/api/v1/stocks/TEST/broker-flow?range=5d")
    assert response.status_code == 200, response.text
    body = response.json()
    buyer = next(row for row in body["broker_series"] if row["broker_code"] == "B0")
    assert body["status"] == "partial"
    assert body["days"][2]["available"] is False
    assert buyer["points"][2]["net_shares"] is None
    assert buyer["points"][2]["cumulative_net_shares"] is None
    assert buyer["points"][1]["cumulative_net_shares"] == 1600
    assert buyer["points"][3]["cumulative_net_shares"] == 2400
