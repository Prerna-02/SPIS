"""Test script to verify anomaly ingestion endpoint."""
import requests
import json

vessels = [
    {"mmsi": "276260000", "lat": 59.4579, "lon": 24.7081, "sog": 0.0, "cog": 180.0, "heading": 0.0, "ship_name": "NAFTA", "ship_type": "tanker"},
    {"mmsi": "276823000", "lat": 59.4585, "lon": 24.6585, "sog": 0.0, "cog": 360.0, "heading": 0.0, "ship_name": "LEIGER", "ship_type": "cargo"},
    {"mmsi": "276330000", "lat": 59.4532, "lon": 24.7371, "sog": 0.1, "cog": 271.0, "heading": 0.0, "ship_name": "HABE-3", "ship_type": "tug"},
]

print(f"Sending {len(vessels)} vessels to http://localhost:8002/live/ingest")
print(f"JSON preview: {json.dumps(vessels[0])}")

try:
    resp = requests.post("http://localhost:8002/live/ingest", json=vessels, timeout=10)
    print(f"\nStatus Code: {resp.status_code}")
    result = resp.json()
    print(f"Response: {json.dumps(result, indent=2)}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

# Check if vessels were stored
print("\n--- Checking /live/vessels ---")
try:
    resp2 = requests.get("http://localhost:8002/live/vessels")
    data = resp2.json()
    print(f"Vessels tracked: {len(data.get('vessels', []))}")
    print(f"Threshold: {data.get('threshold')}")
    for v in data.get('vessels', [])[:5]:
        print(f"  - {v.get('vessel_name')}: score={v.get('score')}, is_anomaly={v.get('is_anomaly')}, risk={v.get('risk_level')}")
except Exception as e:
    print(f"Error checking vessels: {e}")
