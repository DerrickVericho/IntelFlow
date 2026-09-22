"""Generate a reviewable frontend payload from clearly synthetic DEMO data.

Run: uv run python -m src.backend.tests.export_example
"""

import json
from pathlib import Path
from fastapi.testclient import TestClient
from ..cache.store import MemoryCache
from ..config import Settings
from ..main import create_app
from ..sectors.cached import CachedSectorsGateway
from ..services.research import ResearchService
from .fixtures import FixtureTransport, TODAY


def main():
    gateway = CachedSectorsGateway(
        FixtureTransport(), MemoryCache(), Settings.from_env()
    )
    service = ResearchService(gateway, today=lambda: TODAY)
    with TestClient(create_app(service=service)) as client:
        response = client.get("/api/v1/stocks/DEMO/intel-score")
        response.raise_for_status()
        payload = response.json()
    destination = Path("docs/examples/intel-score.demo.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "file": str(destination),
                "synthetic": True,
                "broker_bars": len(payload["flow"]["broker_summary"]["brokers"]),
                "foreign_points": len(payload["flow"]["foreign_flow"]["series"]),
                "liquidity_points": len(payload["flow"]["liquidity"]["series"]),
                "fundamental_metrics": sum(
                    len(g["metrics"]) for g in payload["fundamentals"]["groups"]
                ),
                "scores": {
                    k: payload["scores"][k]["value"]
                    for k in ("flow", "fundamental", "combined")
                },
            }
        )
    )


if __name__ == "__main__":
    main()
