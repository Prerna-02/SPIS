"""
=============================================================================
Port Inventory Configuration - Smart Port Intelligence System
=============================================================================

Defines the port infrastructure model for Tallinn Port:
- Berths (4 total: 2 Old City, 2 Muuga)
- Cranes (6 total, mapped to berths)
- Yard Blocks (3 total with TEU capacity)

Based on TRD v2 Section C.
=============================================================================
"""

from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum


# ---------------------------------------------------------------------------
# ENUMS
# ---------------------------------------------------------------------------

class Terminal(Enum):
    OLD_CITY = "OLD_CITY"
    MUUGA = "MUUGA"


class AssetType(Enum):
    CRANE = "CRANE"
    TRUCK = "TRUCK"
    FORKLIFT = "FORKLIFT"


class CapacityClass(Enum):
    CONTAINER = "CONTAINER"
    BULK = "BULK"
    RO_RO = "RO_RO"
    GENERAL = "GENERAL"


# ---------------------------------------------------------------------------
# DATA CLASSES
# ---------------------------------------------------------------------------

@dataclass
class BerthConfig:
    """Configuration for a berth."""
    berth_id: str
    terminal: Terminal
    max_vessels: int = 1
    capacity_class: CapacityClass = CapacityClass.CONTAINER
    service_rate_base: float = 25.0  # containers/hour baseline


@dataclass
class AssetConfig:
    """Configuration for an asset (crane, truck, etc.)."""
    asset_id: str
    asset_type: AssetType
    home_berth_id: str
    operation_state: str = "OPERATIONAL"
    effective_capacity: float = 1.0


@dataclass
class YardBlockConfig:
    """Configuration for a yard block."""
    yard_id: str
    terminal: Terminal
    capacity_teu: int
    used_teu: int = 0


# ---------------------------------------------------------------------------
# PORT INVENTORY (Tallinn Demo Configuration)
# ---------------------------------------------------------------------------

BERTHS: List[BerthConfig] = [
    # Old City Harbor
    BerthConfig(
        berth_id="B1",
        terminal=Terminal.OLD_CITY,
        capacity_class=CapacityClass.CONTAINER,
        service_rate_base=25.0
    ),
    BerthConfig(
        berth_id="B2",
        terminal=Terminal.OLD_CITY,
        capacity_class=CapacityClass.RO_RO,
        service_rate_base=30.0
    ),
    # Muuga Terminal
    BerthConfig(
        berth_id="B3",
        terminal=Terminal.MUUGA,
        capacity_class=CapacityClass.CONTAINER,
        service_rate_base=40.0
    ),
    BerthConfig(
        berth_id="B4",
        terminal=Terminal.MUUGA,
        capacity_class=CapacityClass.BULK,
        service_rate_base=50.0
    ),
]

ASSETS: List[AssetConfig] = [
    # Cranes for Container berths
    AssetConfig(asset_id="C1", asset_type=AssetType.CRANE, home_berth_id="B1"),
    AssetConfig(asset_id="C2", asset_type=AssetType.CRANE, home_berth_id="B1"),
    AssetConfig(asset_id="C3", asset_type=AssetType.CRANE, home_berth_id="B3"),
    AssetConfig(asset_id="C4", asset_type=AssetType.CRANE, home_berth_id="B3"),
    AssetConfig(asset_id="C5", asset_type=AssetType.CRANE, home_berth_id="B3"),
    AssetConfig(asset_id="C6", asset_type=AssetType.CRANE, home_berth_id="B4"),
]

YARD_BLOCKS: List[YardBlockConfig] = [
    YardBlockConfig(yard_id="Y1", terminal=Terminal.OLD_CITY, capacity_teu=2000, used_teu=1200),
    YardBlockConfig(yard_id="Y2", terminal=Terminal.MUUGA, capacity_teu=5000, used_teu=3500),
    YardBlockConfig(yard_id="Y3", terminal=Terminal.MUUGA, capacity_teu=3000, used_teu=1800),
]


# ---------------------------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------------------------

def get_berths_by_terminal(terminal: Terminal) -> List[BerthConfig]:
    """Get all berths for a specific terminal."""
    return [b for b in BERTHS if b.terminal == terminal]


def get_assets_by_berth(berth_id: str) -> List[AssetConfig]:
    """Get all assets assigned to a specific berth."""
    return [a for a in ASSETS if a.home_berth_id == berth_id]


def get_yard_blocks_by_terminal(terminal: Terminal) -> List[YardBlockConfig]:
    """Get all yard blocks for a specific terminal."""
    return [y for y in YARD_BLOCKS if y.terminal == terminal]


def get_total_yard_capacity() -> Dict[str, int]:
    """Get total yard capacity and usage."""
    total_capacity = sum(y.capacity_teu for y in YARD_BLOCKS)
    total_used = sum(y.used_teu for y in YARD_BLOCKS)
    return {
        "total_capacity_teu": total_capacity,
        "total_used_teu": total_used,
        "utilization_pct": round(100 * total_used / total_capacity, 1) if total_capacity > 0 else 0.0
    }


def get_inventory_summary() -> dict:
    """Get a summary of the port inventory for display."""
    return {
        "berths": {
            "total": len(BERTHS),
            "old_city": len(get_berths_by_terminal(Terminal.OLD_CITY)),
            "muuga": len(get_berths_by_terminal(Terminal.MUUGA)),
        },
        "assets": {
            "total": len(ASSETS),
            "cranes": len([a for a in ASSETS if a.asset_type == AssetType.CRANE]),
        },
        "yard": get_total_yard_capacity(),
    }


# ---------------------------------------------------------------------------
# TESTING
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Port Inventory Configuration:")
    print("=" * 60)
    
    print("\n📍 BERTHS:")
    for b in BERTHS:
        assets = get_assets_by_berth(b.berth_id)
        print(f"  {b.berth_id}: {b.terminal.value} | {b.capacity_class.value} | "
              f"{len(assets)} cranes | {b.service_rate_base} cont/hr")
    
    print("\n🏗️ ASSETS (Cranes):")
    for a in ASSETS:
        print(f"  {a.asset_id}: {a.asset_type.value} @ Berth {a.home_berth_id}")
    
    print("\n📦 YARD BLOCKS:")
    for y in YARD_BLOCKS:
        util = round(100 * y.used_teu / y.capacity_teu, 1)
        print(f"  {y.yard_id}: {y.terminal.value} | {y.used_teu}/{y.capacity_teu} TEU ({util}%)")
    
    print("\n📊 SUMMARY:")
    summary = get_inventory_summary()
    print(f"  Berths: {summary['berths']['total']} total")
    print(f"  Cranes: {summary['assets']['cranes']} total")
    print(f"  Yard: {summary['yard']['utilization_pct']}% utilized")
