"""Add sample vessels to the Knowledge Graph."""
from neo4j_client import get_client
from datetime import datetime, timedelta

client = get_client()
client.connect()

# Add sample vessels approaching Tallinn Port
vessels = [
    ('276000001', 59.47, 24.80, 12.5, 180, 'APPROACHING', 'APPROACH', (datetime.now() + timedelta(hours=2)).isoformat()),
    ('276000002', 59.45, 24.75, 8.0, 90, 'APPROACHING', 'APPROACH', (datetime.now() + timedelta(hours=4)).isoformat()),
    ('276000003', 59.42, 24.85, 0.0, 0, 'WAITING', 'ANCHORAGE', (datetime.now() + timedelta(hours=1)).isoformat()),
    ('276000004', 59.44, 24.78, 0.0, 0, 'BERTHED', 'BERTH_OLDCITY', None),
    ('276000005', 59.48, 24.72, 15.0, 270, 'APPROACHING', 'APPROACH', (datetime.now() + timedelta(hours=6)).isoformat()),
]

for mmsi, lat, lon, sog, cog, status, zone, eta in vessels:
    client.upsert_vessel(mmsi, lat, lon, sog=sog, cog=cog, status=status, zone=zone, eta_to_port=eta)
    print(f'Added vessel {mmsi} - {status}')

snapshot = client.get_snapshot()
print(f'\nTotal vessels: {snapshot["vessels"]["total"]}')
print(f'Berths: {len(snapshot["berths"])}')
print(f'Assets: {len(snapshot["assets"])}')

client.close()
print('\nDone! Neo4j is ready for optimization.')
