"""
=============================================================================
AIS INGESTION PIPELINE - Smart Port Intelligence System
=============================================================================

This script provides a robust AIS data ingestion pipeline with two modes:

1) LIVE MODE (recording):
   - Streams real-time vessel position data from AISStream WebSocket
   - Saves messages to JSONL files in: data/raw/aisstream_logs/
   - Pushes vessel updates to Neo4j Knowledge Graph
   - Auto-reconnects with exponential backoff on disconnection
   - Graceful shutdown on Ctrl+C

2) REPLAY MODE (fallback):
   - Replays previously recorded JSONL files
   - Configurable playback speed (msgs/sec)
   - Can also push to Neo4j for testing

USAGE:
------
# Live mode (default):
python app.py --mode live

# Live mode with Neo4j integration:
python app.py --mode live --neo4j

# Replay mode with Neo4j:
python app.py --mode replay --file ../../data/raw/aisstream_logs/<filename>.jsonl --rate 5 --neo4j

ARGUMENTS:
----------
--mode      : 'live' or 'replay' (default: live)
--neo4j     : Enable Neo4j integration (push vessels to KG)
--file      : Path to JSONL file (required for replay mode)
--rate      : Messages per second for replay (default: 5.0)
--min-sog   : Only display vessels with Speed Over Ground >= this value (default: 0.0)

ENVIRONMENT:
------------
Create a .env file with:
    AISSTREAM_API_KEY=your_api_key_here
    NEO4J_URI=bolt://localhost:7687
    NEO4J_USER=neo4j
    NEO4J_PASSWORD=portintel2026

OUTPUT FILES:
-------------
Logged to: data/raw/aisstream_logs/aisstream_tallinn_YYYYMMDD_HHMMSS.jsonl
Each line contains: timestamp, mmsi, lat, lon, sog, cog, heading, message_type
=============================================================================
"""

import asyncio
import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Callable, Optional

import websockets
from dotenv import load_dotenv

# Add parent path for kg module imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "kg"))

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

load_dotenv()

# Also load kg/.env for Neo4j credentials
kg_env = os.path.join(os.path.dirname(__file__), "..", "kg", ".env")
if os.path.exists(kg_env):
    load_dotenv(kg_env)

URI = "wss://stream.aisstream.io/v0/stream"

# Tallinn area bounding box (harbor + approaches). Adjust if needed.
BOUNDING_BOXES = [
    [[59.60, 24.55], [59.35, 25.15]],
]

FILTER_MESSAGE_TYPES = ["PositionReport", "ShipStaticData"]

# ---------------------------------------------------------------------------
# ITU/IMO SHIP TYPE MAPPING
# ---------------------------------------------------------------------------
# Official AIS Ship Type codes as defined by ITU-R M.1371
# https://www.itu.int/rec/R-REC-M.1371/en

SHIP_TYPE_CODES = {
    # 20-29: Wing in Ground (WIG)
    **{i: "wig" for i in range(20, 30)},
    # 30-39: Fishing
    **{i: "fishing" for i in range(30, 40)},
    # 40-49: High-speed craft
    **{i: "highspeed" for i in range(40, 50)},
    # 50-59: Special craft (tugs, pilot, SAR, etc.)
    **{i: "tug" for i in range(50, 60)},
    # 60-69: Passenger vessels (ferries, cruise ships)
    **{i: "passenger" for i in range(60, 70)},
    # 70-79: Cargo vessels
    **{i: "cargo" for i in range(70, 80)},
    # 80-89: Tankers
    **{i: "tanker" for i in range(80, 90)},
    # 90-99: Other
    **{i: "other" for i in range(90, 100)},
}

def get_ship_type_category(ship_type_code: int) -> str:
    """Convert ITU ship type code to category name."""
    if ship_type_code is None:
        return "unknown"
    return SHIP_TYPE_CODES.get(ship_type_code, "other")

# ---------------------------------------------------------------------------
# LOGGING SETUP
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# NEO4J INTEGRATION (optional)
# ---------------------------------------------------------------------------

_neo4j_client = None
_zones_module = None


def init_neo4j():
    """Initialize Neo4j client if available."""
    global _neo4j_client, _zones_module
    try:
        from neo4j_client import Neo4jClient
        import zones as zones_module
        
        _neo4j_client = Neo4jClient()
        _neo4j_client.connect()
        _zones_module = zones_module
        logger.info("[NEO4J] Neo4j integration enabled")
        return True
    except ImportError as e:
        logger.warning(f"[WARN] Neo4j modules not found: {e}")
        return False
    except Exception as e:
        logger.warning(f"[WARN] Neo4j connection failed: {e}")
        return False


def close_neo4j():
    """Close Neo4j connection."""
    global _neo4j_client
    if _neo4j_client:
        _neo4j_client.close()
        _neo4j_client = None


def push_vessel_to_neo4j(record: dict) -> bool:
    """
    Push a vessel record to Neo4j with zone classification.
    
    Includes ship_type (ITU category) and ship_name from AIS metadata.
    Returns True if successful, False otherwise.
    """
    global _neo4j_client, _zones_module
    
    if not _neo4j_client or not _zones_module:
        return False
    
    try:
        mmsi = str(record.get("mmsi", ""))
        lat = record.get("lat")
        lon = record.get("lon")
        sog = record.get("sog")
        cog = record.get("cog")
        heading = record.get("heading")
        ship_type = record.get("ship_type")  # ITU category: cargo, tanker, etc.
        ship_name = record.get("ship_name")
        
        if not mmsi or lat is None or lon is None:
            return False
        
        # Classify position using zones module
        classification = _zones_module.classify_vessel_position(
            lat=float(lat),
            lon=float(lon),
            sog=float(sog) if sog is not None else 0.0,
            mmsi=mmsi
        )
        
        # Upsert vessel to Neo4j with ship_type and ship_name
        _neo4j_client.upsert_vessel(
            mmsi=mmsi,
            lat=float(lat),
            lon=float(lon),
            sog=float(sog) if sog is not None else None,
            cog=float(cog) if cog is not None else None,
            heading=float(heading) if heading is not None else None,
            zone=classification["zone"],
            status=classification["status"],
            eta_to_port=classification["eta_to_port"],
            ship_type=ship_type,
            ship_name=ship_name,
        )
        
        # Link vessel to zone node
        zone_id = classification["zone"]
        if zone_id != "OUTSIDE":
            _neo4j_client.link_vessel_to_zone(mmsi, zone_id)
        
        return True
        
    except Exception as e:
        logger.debug(f"Neo4j push error: {e}")
        return False


# ---------------------------------------------------------------------------
# ANOMALY SERVICE INTEGRATION
# ---------------------------------------------------------------------------

ANOMALY_SERVICE_URL = os.getenv("ANOMALY_SERVICE_URL", "http://localhost:8002")


def push_vessel_to_anomaly(record: dict) -> bool:
    """
    Push a vessel record to the anomaly detection service.
    Sends immediately for real-time updates.
    """
    import requests
    
    ship_name = record.get("ship_name", "UNKNOWN")
    print(f"[DEBUG] push_vessel_to_anomaly called for {ship_name}")
    
    try:
        vessel_data = {
            "mmsi": str(record.get("mmsi", "")),
            "lat": record.get("lat"),
            "lon": record.get("lon"),
            "sog": record.get("sog", 0),
            "cog": record.get("cog", 0),
            "heading": record.get("heading", 0),
            "ship_name": ship_name,
            "ship_type": record.get("ship_type", "unknown")
        }
        
        # Send immediately - no buffering for real-time updates
        print(f"[DEBUG] Sending POST to {ANOMALY_SERVICE_URL}/live/ingest")
        response = requests.post(
            f"{ANOMALY_SERVICE_URL}/live/ingest",
            json=[vessel_data],  # Send as array
            timeout=5
        )
        print(f"[DEBUG] Response status: {response.status_code}")
        
        if response.ok:
            result = response.json()
            ingested = result.get('ingested', 0)
            anomalies = result.get('anomalies', 0)
            print(f"[DEBUG] Ingested: {ingested}, Anomalies: {anomalies}")
            if ingested > 0:
                print(f"[ANOMALY OK] {vessel_data['ship_name'] or vessel_data['mmsi']} -> ingested")
            return True
        else:
            print(f"[ANOMALY FAIL] Push failed: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError as e:
        print(f"[DEBUG] ConnectionError: {e}")
        return False
    except requests.exceptions.Timeout as e:
        print(f"[DEBUG] Timeout: {e}")
        return False
    except Exception as e:
        print(f"[DEBUG] Exception: {type(e).__name__}: {e}")
        return False


# ---------------------------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------------------------


def build_subscribe_message() -> dict:
    """Build the subscription message for AISStream WebSocket."""
    api_key = os.getenv("AISSTREAM_API_KEY")
    if not api_key:
        raise ValueError("Missing AISSTREAM_API_KEY in your .env")

    return {
        "APIKey": api_key,
        "BoundingBoxes": BOUNDING_BOXES,
        "FilterMessageTypes": FILTER_MESSAGE_TYPES,
    }


def ensure_log_dir() -> str:
    """Create and return the log directory path."""
    log_dir = os.path.join("..", "..", "data", "raw", "aisstream_logs")
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


def new_logfile_path(log_dir: str) -> str:
    """Generate a new timestamped log file path."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return os.path.join(log_dir, f"aisstream_tallinn_{ts}.jsonl")


def extract_minimal_fields(payload: dict) -> dict:
    """
    Extract a minimal normalized record from AISStream payload.
    Returns a dict suitable for writing as one JSONL line.
    Handles both PositionReport and ShipStaticData message types.
    """
    msg_obj = payload.get("Message", {})
    meta = payload.get("MetaData", {})
    message_type = payload.get("MessageType")
    
    # Handle different message types
    pos = msg_obj.get("PositionReport", {})
    static = msg_obj.get("ShipStaticData", {})

    # MMSI can be in various places depending on message format
    mmsi = (
        pos.get("MMSI")
        or pos.get("UserID")
        or static.get("MMSI")
        or static.get("UserID")
        or msg_obj.get("MMSI")
        or msg_obj.get("UserID")
        or meta.get("MMSI")
        or meta.get("Mmsi")
    )
    
    # Ship type from MetaData or ShipStaticData (ITU/IMO standard code 0-99)
    ship_type_code = static.get("Type") or meta.get("ShipType")
    ship_type_category = get_ship_type_category(ship_type_code)
    
    # Ship name - prefer ShipStaticData, fallback to MetaData
    ship_name = static.get("Name", "").strip() or meta.get("ShipName", "").strip() or None

    # Base record with common fields
    record = {
        "ingest_ts_utc": datetime.now(timezone.utc).isoformat(),
        "message_type": message_type,
        "mmsi": mmsi,
        "ship_type_code": ship_type_code,
        "ship_type": ship_type_category,
        "ship_name": ship_name,
    }
    
    # Add position data if PositionReport
    if pos:
        record.update({
            "lat": pos.get("Latitude"),
            "lon": pos.get("Longitude"),
            "sog": pos.get("Sog"),  # Speed Over Ground (knots)
            "cog": pos.get("Cog"),  # Course Over Ground (degrees)
            "heading": pos.get("Heading"),
            "nav_status": pos.get("NavigationalStatus"),  # 0=underway, 1=anchored, 5=moored, etc.
            "ais_ts": pos.get("Timestamp") or msg_obj.get("Timestamp"),
        })
    
    # Add static data if ShipStaticData
    if static:
        # ETA - combine into readable format
        eta_month = static.get("EtaMonth")
        eta_day = static.get("EtaDay")
        eta_hour = static.get("EtaHour")
        eta_minute = static.get("EtaMinute")
        eta_str = None
        if eta_month and eta_day:
            eta_str = f"{eta_month:02d}-{eta_day:02d} {eta_hour or 0:02d}:{eta_minute or 0:02d}"
        
        # Dimensions
        dim = static.get("Dimension", {})
        length = None
        width = None
        if dim:
            a, b = dim.get("A", 0), dim.get("B", 0)
            c, d = dim.get("C", 0), dim.get("D", 0)
            if a or b:
                length = (a or 0) + (b or 0)
            if c or d:
                width = (c or 0) + (d or 0)
        
        record.update({
            "destination": static.get("Destination", "").strip() or None,
            "eta": eta_str,
            "imo": static.get("ImoNumber"),
            "callsign": static.get("CallSign", "").strip() or None,
            "length": length,
            "width": width,
            "draught": static.get("MaximumStaticDraught"),
        })
        
        # Use lat/lon from MetaData for static messages (approximate position)
        if not record.get("lat"):
            record["lat"] = meta.get("latitude")
            record["lon"] = meta.get("longitude")
    
    return record


def valid_lat_lon(lat, lon) -> bool:
    """Validate latitude and longitude values."""
    if lat is None or lon is None:
        return False
    return (-90 <= float(lat) <= 90) and (-180 <= float(lon) <= 180)


def format_vessel_line(record: dict, zone: str = None, status: str = None) -> str:
    """Format a vessel record for console output with ship type, COG, and static data."""
    message_type = record.get('message_type', '')
    cog = record.get('cog')
    sog = record.get('sog')
    ship_type = record.get('ship_type', 'unknown')
    ship_name = record.get('ship_name') or ''
    
    # Ship type prefix
    type_prefix = {
        'cargo': '[CARGO]', 'tanker': '[TANKER]', 'passenger': '[PASS]', 'fishing': '[FISH]',
        'tug': '[TUG]', 'highspeed': '[FAST]', 'wig': '[WIG]', 'other': '[OTHER]', 'unknown': '[?]'
    }.get(ship_type, '[SHIP]')
    
    # Handle PositionReport messages
    if message_type == "PositionReport":
        lat = record.get('lat')
        lon = record.get('lon')
        
        # Format COG (Course Over Ground)
        cog_str = f"cog={cog:.1f}°" if cog is not None else ""
        sog_str = f"sog={sog}" if sog is not None else ""
        
        base = (
            f"{type_prefix} MMSI={record.get('mmsi')} "
            f"[{ship_type.upper()}] "
            f"lat={lat:.4f} lon={lon:.4f} "
            f"{sog_str} {cog_str}"
        )
        if ship_name:
            base = f"{type_prefix} {ship_name[:15]:15} | MMSI={record.get('mmsi')} lat={lat:.4f} lon={lon:.4f} {sog_str} {cog_str}"
        if zone and status:
            return f"{base} | {zone} → {status}"
        return base
    
    # Handle ShipStaticData messages
    elif message_type == "ShipStaticData":
        dest = record.get('destination') or '-'
        eta = record.get('eta') or '-'
        length = record.get('length')
        imo = record.get('imo')
        
        dim_str = f"{length}m" if length else "-"
        imo_str = f"IMO={imo}" if imo else ""
        
        base = (
            f"[STATIC] {ship_name[:15]:15} | MMSI={record.get('mmsi')} "
            f"[{ship_type.upper()}] "
            f"-> {dest[:20]} ETA={eta} {dim_str} {imo_str}"
        )
        return base.strip()
    
    # Fallback for other message types
    else:
        return f"{type_prefix} MMSI={record.get('mmsi')} [{message_type}]"


# ---------------------------------------------------------------------------
# LIVE MODE
# ---------------------------------------------------------------------------


async def live_mode(min_sog: float = 0.0, enable_neo4j: bool = False):
    """
    Connect to AISStream WebSocket and stream live AIS data.
    
    - Saves all messages to JSONL file
    - Optionally pushes to Neo4j
    - Auto-reconnects with exponential backoff on failure
    - Graceful shutdown on KeyboardInterrupt
    """
    subscribe_msg = build_subscribe_message()
    log_dir = ensure_log_dir()
    log_file = new_logfile_path(log_dir)

    backoff = 2  # seconds
    max_backoff = 60
    neo4j_count = 0

    # Initialize Neo4j if requested
    if enable_neo4j:
        if not init_neo4j():
            logger.warning("Continuing without Neo4j integration")
            enable_neo4j = False

    logger.info(f"[LOG] Logging to: {log_file}")
    logger.info(f"[NEO4J] {'enabled' if enable_neo4j else 'disabled'}")
    logger.info("[LIVE] LIVE mode starting... (Ctrl+C to stop)")

    try:
        while True:
            try:
                async with websockets.connect(URI, ping_interval=20, ping_timeout=20) as ws:
                    await ws.send(json.dumps(subscribe_msg))
                    logger.info("[CONNECTED] Connected + subscribed. Listening...")

                    # Reset backoff on successful connection
                    backoff = 2

                    # Open log file in append mode
                    with open(log_file, "a", encoding="utf-8") as f:
                        while True:
                            raw = await ws.recv()
                            payload = json.loads(raw)

                            record = extract_minimal_fields(payload)
                            message_type = record.get("message_type")

                            # Save JSONL record
                            f.write(json.dumps(record) + "\n")
                            f.flush()

                            lat = record.get("lat")
                            lon = record.get("lon")
                            sog = record.get("sog")

                            # Handle ShipStaticData (no position, but has destination/ETA)
                            if message_type == "ShipStaticData":
                                # Display static data regardless of position
                                logger.info(format_vessel_line(record))
                                continue

                            # For PositionReport, require valid coordinates
                            if not valid_lat_lon(lat, lon):
                                continue

                            # Push to Neo4j if enabled (only for position reports)
                            zone = None
                            status = None
                            if enable_neo4j:
                                if push_vessel_to_neo4j(record):
                                    neo4j_count += 1
                                    # Get classification for display
                                    if _zones_module:
                                        cls = _zones_module.classify_vessel_position(
                                            lat=float(lat), lon=float(lon), 
                                            sog=float(sog) if sog else 0.0
                                        )
                                        zone = cls["zone"]
                                        status = cls["status"]
                            
                            # Always push to anomaly service for real-time scoring
                            push_vessel_to_anomaly(record)

                            # Filter by minimum speed if specified
                            if sog is not None:
                                try:
                                    if float(sog) < min_sog:
                                        continue
                                except ValueError:
                                    pass

                            logger.info(format_vessel_line(record, zone, status))

            except KeyboardInterrupt:
                raise

            except Exception as e:
                logger.warning(f"[WARN] Live stream error: {type(e).__name__}: {e}")
                logger.info(f"[RETRY] Reconnecting in {backoff}s...")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)

    except KeyboardInterrupt:
        logger.info(f"\n[STOP] Stopped by user. Pushed {neo4j_count} vessels to Neo4j.")
    finally:
        if enable_neo4j:
            close_neo4j()


# ---------------------------------------------------------------------------
# REPLAY MODE
# ---------------------------------------------------------------------------


async def replay_mode(
    file_path: str,
    rate: float = 5.0,
    min_sog: float = 0.0,
    enable_neo4j: bool = False,
    callback: Optional[Callable[[dict], None]] = None,
):
    """
    Replay a JSONL file created by live_mode, emitting messages at `rate` msgs/sec.
    
    Args:
        file_path: Path to the JSONL file to replay
        rate: Number of messages per second to emit
        min_sog: Minimum Speed Over Ground filter for display
        enable_neo4j: Push vessels to Neo4j
        callback: Optional callback function(record) for downstream processing
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Replay file not found: {file_path}")

    delay = 1.0 / max(rate, 0.1)
    neo4j_count = 0

    # Initialize Neo4j if requested
    if enable_neo4j:
        if not init_neo4j():
            logger.warning("Continuing without Neo4j integration")
            enable_neo4j = False

    logger.info(f"[REPLAY] REPLAY mode starting from: {file_path}")
    logger.info(f"[RATE] Rate: {rate} msgs/sec (delay={delay:.3f}s)")
    logger.info(f"[NEO4J] {'enabled' if enable_neo4j else 'disabled'}")
    logger.info("Press Ctrl+C to stop.\n")

    message_count = 0
    displayed_count = 0

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue

                record = json.loads(line)
                message_count += 1

                # Invoke callback if provided
                if callback is not None:
                    try:
                        callback(record)
                    except Exception as cb_err:
                        logger.warning(f"Callback error: {cb_err}")

                lat = record.get("lat")
                lon = record.get("lon")
                sog = record.get("sog")

                if not valid_lat_lon(lat, lon):
                    await asyncio.sleep(delay)
                    continue

                # Push to Neo4j if enabled
                zone = None
                status = None
                if enable_neo4j:
                    if push_vessel_to_neo4j(record):
                        neo4j_count += 1
                        if _zones_module:
                            cls = _zones_module.classify_vessel_position(
                                lat=float(lat), lon=float(lon),
                                sog=float(sog) if sog else 0.0
                            )
                            zone = cls["zone"]
                            status = cls["status"]

                if sog is not None:
                    try:
                        if float(sog) < min_sog:
                            await asyncio.sleep(delay)
                            continue
                    except ValueError:
                        pass

                displayed_count += 1
                logger.info(format_vessel_line(record, zone, status))
                await asyncio.sleep(delay)

        logger.info(f"\n[DONE] Replay complete. Total: {message_count}, Displayed: {displayed_count}, Neo4j: {neo4j_count}")

    except KeyboardInterrupt:
        logger.info(f"\n[STOP] Replay stopped. Pushed {neo4j_count} vessels to Neo4j.")
    finally:
        if enable_neo4j:
            close_neo4j()


# ---------------------------------------------------------------------------
# CLI ARGUMENT PARSING
# ---------------------------------------------------------------------------


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="AISStream ingestion: live + replay modes with Neo4j integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python app.py --mode live
  python app.py --mode live --neo4j
  python app.py --mode replay --file ../../data/raw/aisstream_logs/file.jsonl --rate 5 --neo4j
        """,
    )
    parser.add_argument(
        "--mode",
        choices=["live", "replay"],
        default="live",
        help="Run mode: live (AISStream) or replay (from JSONL file).",
    )
    parser.add_argument(
        "--neo4j",
        action="store_true",
        help="Enable Neo4j integration (push vessels to Knowledge Graph).",
    )
    parser.add_argument(
        "--file",
        type=str,
        default="",
        help="Replay file path (required if --mode replay).",
    )
    parser.add_argument(
        "--rate",
        type=float,
        default=5.0,
        help="Replay rate in msgs/sec (only for replay mode).",
    )
    parser.add_argument(
        "--min-sog",
        type=float,
        default=0.0,
        help="Only print records with sog >= min_sog (useful to see moving vessels).",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------


async def main():
    """Main entry point."""
    args = parse_args()

    if args.mode == "live":
        await live_mode(min_sog=args.min_sog, enable_neo4j=args.neo4j)
    else:
        if not args.file:
            raise ValueError("Replay mode requires --file path/to/file.jsonl")
        await replay_mode(
            file_path=args.file,
            rate=args.rate,
            min_sog=args.min_sog,
            enable_neo4j=args.neo4j
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n[STOP] Stopped by user.")
