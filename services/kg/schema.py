"""
=============================================================================
Schema Initialization - Smart Port Intelligence System
=============================================================================

Initializes the Neo4j Knowledge Graph schema:
- Creates constraints and indexes
- Creates Zone nodes
- Creates Berth, Asset, and YardBlock nodes from config

Run this script once after Neo4j is started:
    python schema.py
=============================================================================
"""

import logging
from neo4j_client import get_client
from config import BERTHS, ASSETS, YARD_BLOCKS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CONSTRAINTS AND INDEXES
# ---------------------------------------------------------------------------

CONSTRAINTS = [
    "CREATE CONSTRAINT vessel_mmsi IF NOT EXISTS FOR (v:Vessel) REQUIRE v.mmsi IS UNIQUE",
    "CREATE CONSTRAINT zone_id IF NOT EXISTS FOR (z:Zone) REQUIRE z.zone_id IS UNIQUE",
    "CREATE CONSTRAINT berth_id IF NOT EXISTS FOR (b:Berth) REQUIRE b.berth_id IS UNIQUE",
    "CREATE CONSTRAINT asset_id IF NOT EXISTS FOR (a:Asset) REQUIRE a.asset_id IS UNIQUE",
    "CREATE CONSTRAINT yard_id IF NOT EXISTS FOR (y:YardBlock) REQUIRE y.yard_id IS UNIQUE",
    "CREATE CONSTRAINT plan_id IF NOT EXISTS FOR (p:Plan) REQUIRE p.plan_id IS UNIQUE",
    "CREATE CONSTRAINT impact_id IF NOT EXISTS FOR (i:Impact) REQUIRE i.impact_id IS UNIQUE",
    "CREATE CONSTRAINT portcall_id IF NOT EXISTS FOR (pc:PortCall) REQUIRE pc.portcall_id IS UNIQUE",
]

INDEXES = [
    "CREATE INDEX vessel_status IF NOT EXISTS FOR (v:Vessel) ON (v.status)",
    "CREATE INDEX vessel_zone IF NOT EXISTS FOR (v:Vessel) ON (v.zone)",
    "CREATE INDEX asset_type IF NOT EXISTS FOR (a:Asset) ON (a.asset_type)",
]


# ---------------------------------------------------------------------------
# ZONE DEFINITIONS
# ---------------------------------------------------------------------------

ZONES = [
    ("APPROACH", "APPROACH_ZONE"),
    ("ANCHORAGE", "ANCHORAGE_ZONE"),
    ("BERTH_OLDCITY", "BERTH_ZONE"),
    ("BERTH_MUUGA", "BERTH_ZONE"),
]


# ---------------------------------------------------------------------------
# SCHEMA INITIALIZATION
# ---------------------------------------------------------------------------

def init_constraints(client) -> None:
    """Create all constraints."""
    logger.info("Creating constraints...")
    for constraint in CONSTRAINTS:
        try:
            client.execute_write(constraint)
        except Exception as e:
            # Constraint may already exist
            if "already exists" not in str(e).lower():
                logger.warning(f"Constraint warning: {e}")


def init_indexes(client) -> None:
    """Create all indexes."""
    logger.info("Creating indexes...")
    for index in INDEXES:
        try:
            client.execute_write(index)
        except Exception as e:
            if "already exists" not in str(e).lower():
                logger.warning(f"Index warning: {e}")


def init_zones(client) -> None:
    """Create zone nodes."""
    logger.info("Creating zone nodes...")
    for zone_id, zone_type in ZONES:
        client.create_zone(zone_id, zone_type)
    logger.info(f"  Created {len(ZONES)} zones")


def init_berths(client) -> None:
    """Create berth nodes from config."""
    logger.info("Creating berth nodes...")
    for berth in BERTHS:
        client.upsert_berth(
            berth_id=berth.berth_id,
            terminal=berth.terminal.value,
            capacity_class=berth.capacity_class.value,
            max_vessels=berth.max_vessels,
            service_rate_base=berth.service_rate_base,
        )
    logger.info(f"  Created {len(BERTHS)} berths")


def init_assets(client) -> None:
    """Create asset nodes from config and link to berths."""
    logger.info("Creating asset nodes...")
    for asset in ASSETS:
        client.upsert_asset(
            asset_id=asset.asset_id,
            asset_type=asset.asset_type.value,
            operation_state=asset.operation_state,
            effective_capacity=asset.effective_capacity,
        )
        # Link asset to home berth
        client.link_berth_to_asset(asset.home_berth_id, asset.asset_id)
    logger.info(f"  Created {len(ASSETS)} assets with berth links")


def init_yard_blocks(client) -> None:
    """Create yard block nodes from config."""
    logger.info("Creating yard block nodes...")
    for yard in YARD_BLOCKS:
        client.upsert_yard_block(
            yard_id=yard.yard_id,
            terminal=yard.terminal.value,
            capacity_teu=yard.capacity_teu,
            used_teu=yard.used_teu,
        )
    logger.info(f"  Created {len(YARD_BLOCKS)} yard blocks")


def init_schema() -> None:
    """
    Initialize the complete KG schema.
    
    This is idempotent - safe to run multiple times.
    """
    client = get_client()
    
    try:
        client.connect()
        
        logger.info("=" * 60)
        logger.info("Initializing Neo4j Knowledge Graph Schema")
        logger.info("=" * 60)
        
        init_constraints(client)
        init_indexes(client)
        init_zones(client)
        init_berths(client)
        init_assets(client)
        init_yard_blocks(client)
        
        logger.info("=" * 60)
        logger.info("✅ Schema initialization complete!")
        logger.info("=" * 60)
        
        # Print summary
        snapshot = client.get_snapshot()
        logger.info(f"\nKG Summary:")
        logger.info(f"  Berths: {len(snapshot['berths'])}")
        logger.info(f"  Assets: {len(snapshot['assets'])}")
        logger.info(f"  Yard Blocks: {len(snapshot['yard_blocks'])}")
        logger.info(f"  Vessels: {snapshot['vessels']['total']}")
        
    except Exception as e:
        logger.error(f"❌ Schema initialization failed: {e}")
        raise
    finally:
        client.close()


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    init_schema()
