"""
=============================================================================
Zone Classification Module - Smart Port Intelligence System
=============================================================================

Classifies vessel positions into zones (APPROACH, ANCHORAGE, BERTH) and
derives vessel status and ETA based on TRD v2 specifications.

Zone Definitions (Tallinn Port):
- APPROACH: lat [59.30, 59.65], lon [24.45, 25.20]
- ANCHORAGE: lat [59.45, 59.56], lon [24.55, 24.88]
- BERTH_OLDCITY: lat [59.43, 59.46], lon [24.72, 24.80]
- BERTH_MUUGA: lat [59.48, 59.56], lon [24.88, 25.07]
=============================================================================
"""

from dataclasses import dataclass
from enum import Enum
from math import radians, sin, cos, sqrt, atan2
from typing import Optional, Tuple
from datetime import datetime, timezone, timedelta


# ---------------------------------------------------------------------------
# ENUMS
# ---------------------------------------------------------------------------

class ZoneType(Enum):
    APPROACH = "APPROACH"
    ANCHORAGE = "ANCHORAGE"
    BERTH_OLDCITY = "BERTH_OLDCITY"
    BERTH_MUUGA = "BERTH_MUUGA"
    OUTSIDE = "OUTSIDE"


class VesselStatus(Enum):
    APPROACHING = "APPROACHING"
    WAITING = "WAITING"
    BERTHED = "BERTHED"
    IN_TRANSIT = "IN_TRANSIT"


# ---------------------------------------------------------------------------
# ZONE BOUNDING BOXES (from TRD v2 Section A)
# ---------------------------------------------------------------------------

@dataclass
class BoundingBox:
    """Axis-aligned bounding box defined by lat/lon ranges."""
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float
    
    def contains(self, lat: float, lon: float) -> bool:
        """Check if a point is inside this bounding box."""
        return (self.lat_min <= lat <= self.lat_max and
                self.lon_min <= lon <= self.lon_max)


# Zone definitions from TRD v2 Section A
ZONES = {
    ZoneType.BERTH_OLDCITY: BoundingBox(
        lat_min=59.43, lat_max=59.46,
        lon_min=24.72, lon_max=24.80
    ),
    ZoneType.BERTH_MUUGA: BoundingBox(
        lat_min=59.48, lat_max=59.56,
        lon_min=24.88, lon_max=25.07
    ),
    ZoneType.ANCHORAGE: BoundingBox(
        lat_min=59.45, lat_max=59.56,
        lon_min=24.55, lon_max=24.88
    ),
    ZoneType.APPROACH: BoundingBox(
        lat_min=59.30, lat_max=59.65,
        lon_min=24.45, lon_max=25.20
    ),
}

# Port reference point for ETA calculation (TRD v2 Section B)
PORT_REF = (59.45, 24.75)  # Near central Tallinn harbor

# Speed thresholds
SOG_MIN_MOVING = 0.5  # knots - below this, vessel is considered stationary


# ---------------------------------------------------------------------------
# ZONE CLASSIFICATION
# ---------------------------------------------------------------------------

def classify_zone(lat: float, lon: float) -> ZoneType:
    """
    Classify a position into a zone type.
    
    Priority order (most specific first):
    1. BERTH zones (Old City, Muuga)
    2. ANCHORAGE zone
    3. APPROACH zone
    4. OUTSIDE (not in any zone)
    """
    # Check berth zones first (most specific)
    if ZONES[ZoneType.BERTH_OLDCITY].contains(lat, lon):
        return ZoneType.BERTH_OLDCITY
    
    if ZONES[ZoneType.BERTH_MUUGA].contains(lat, lon):
        return ZoneType.BERTH_MUUGA
    
    # Check anchorage
    if ZONES[ZoneType.ANCHORAGE].contains(lat, lon):
        return ZoneType.ANCHORAGE
    
    # Check approach (largest zone)
    if ZONES[ZoneType.APPROACH].contains(lat, lon):
        return ZoneType.APPROACH
    
    return ZoneType.OUTSIDE


def is_berth_zone(zone: ZoneType) -> bool:
    """Check if a zone type is a berth zone."""
    return zone in (ZoneType.BERTH_OLDCITY, ZoneType.BERTH_MUUGA)


# ---------------------------------------------------------------------------
# STATUS DERIVATION
# ---------------------------------------------------------------------------

def derive_status(zone: ZoneType, sog: Optional[float]) -> VesselStatus:
    """
    Derive vessel status from zone and speed over ground.
    
    Rules (from TRD v2 Section A5):
    - BERTH zone + sog < 0.5 → BERTHED
    - ANCHORAGE zone + sog < 0.5 → WAITING
    - APPROACH zone + sog >= 0.5 → APPROACHING
    - Otherwise → IN_TRANSIT
    """
    if sog is None:
        sog = 0.0
    
    if is_berth_zone(zone) and sog < SOG_MIN_MOVING:
        return VesselStatus.BERTHED
    
    if zone == ZoneType.ANCHORAGE and sog < SOG_MIN_MOVING:
        return VesselStatus.WAITING
    
    if zone == ZoneType.APPROACH and sog >= SOG_MIN_MOVING:
        return VesselStatus.APPROACHING
    
    return VesselStatus.IN_TRANSIT


# ---------------------------------------------------------------------------
# ETA CALCULATION
# ---------------------------------------------------------------------------

def haversine_distance_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great-circle distance between two points in nautical miles.
    
    Uses Haversine formula.
    """
    R_EARTH_KM = 6371.0
    KM_TO_NM = 0.539957
    
    lat1_rad, lon1_rad = radians(lat1), radians(lon1)
    lat2_rad, lon2_rad = radians(lat2), radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    
    distance_km = R_EARTH_KM * c
    return distance_km * KM_TO_NM


class ETASmoother:
    """
    Exponential Moving Average smoother for SOG values per vessel.
    
    Keeps track of smoothed SOG for each MMSI to reduce noise.
    """
    
    def __init__(self, alpha: float = 0.3):
        """
        Initialize smoother.
        
        Args:
            alpha: Smoothing factor (0-1). Higher = more responsive to new values.
        """
        self.alpha = alpha
        self._sog_ema: dict[str, float] = {}
    
    def smooth_sog(self, mmsi: str, sog: float) -> float:
        """
        Apply EMA smoothing to SOG for a vessel.
        
        Returns smoothed SOG value.
        """
        if mmsi not in self._sog_ema:
            self._sog_ema[mmsi] = sog
        else:
            self._sog_ema[mmsi] = self.alpha * sog + (1 - self.alpha) * self._sog_ema[mmsi]
        
        return self._sog_ema[mmsi]
    
    def get_smoothed_sog(self, mmsi: str) -> Optional[float]:
        """Get the current smoothed SOG for a vessel."""
        return self._sog_ema.get(mmsi)
    
    def clear(self, mmsi: Optional[str] = None):
        """Clear smoothing history for one or all vessels."""
        if mmsi:
            self._sog_ema.pop(mmsi, None)
        else:
            self._sog_ema.clear()


# Global smoother instance
_eta_smoother = ETASmoother(alpha=0.3)


def calculate_eta(
    lat: float,
    lon: float,
    sog: float,
    mmsi: Optional[str] = None,
    use_smoothing: bool = True
) -> Tuple[Optional[datetime], float, str]:
    """
    Calculate ETA to port reference point.
    
    Args:
        lat: Current latitude
        lon: Current longitude
        sog: Speed over ground (knots)
        mmsi: Vessel MMSI (for EMA smoothing)
        use_smoothing: Whether to apply EMA smoothing to SOG
    
    Returns:
        Tuple of (eta_datetime, eta_hours, confidence)
        - eta_datetime: Estimated time of arrival (UTC)
        - eta_hours: Hours until arrival
        - confidence: "high", "medium", or "low"
    """
    # Calculate distance to port
    distance_nm = haversine_distance_nm(lat, lon, PORT_REF[0], PORT_REF[1])
    
    # Apply smoothing if MMSI provided
    if use_smoothing and mmsi:
        sog_smooth = _eta_smoother.smooth_sog(mmsi, sog)
    else:
        sog_smooth = sog
    
    # Determine confidence based on SOG stability
    if sog_smooth >= 5.0:
        confidence = "high"
    elif sog_smooth >= SOG_MIN_MOVING:
        confidence = "medium"
    else:
        confidence = "low"
    
    # Calculate ETA
    if sog_smooth < SOG_MIN_MOVING:
        # Vessel is stationary - use minimum speed assumption
        sog_smooth = SOG_MIN_MOVING
        confidence = "low"
    
    eta_hours = distance_nm / sog_smooth
    eta_datetime = datetime.now(timezone.utc) + timedelta(hours=eta_hours)
    
    return eta_datetime, eta_hours, confidence


def get_eta_smoother() -> ETASmoother:
    """Get the global ETA smoother instance."""
    return _eta_smoother


# ---------------------------------------------------------------------------
# CONVENIENCE FUNCTIONS
# ---------------------------------------------------------------------------

def classify_vessel_position(
    lat: float,
    lon: float,
    sog: Optional[float],
    mmsi: Optional[str] = None
) -> dict:
    """
    Classify a vessel position and return all derived fields.
    
    Returns dict with:
    - zone: ZoneType
    - status: VesselStatus
    - eta_to_port: datetime or None
    - eta_hours: float
    - eta_confidence: str
    """
    zone = classify_zone(lat, lon)
    status = derive_status(zone, sog)
    
    # Only calculate ETA if vessel is approaching (not already at port)
    if zone == ZoneType.OUTSIDE:
        eta_dt, eta_hours, confidence = None, 0.0, "none"
    elif is_berth_zone(zone) or (zone == ZoneType.ANCHORAGE and (sog or 0) < SOG_MIN_MOVING):
        # Already at port
        eta_dt, eta_hours, confidence = None, 0.0, "arrived"
    else:
        eta_dt, eta_hours, confidence = calculate_eta(lat, lon, sog or 0.0, mmsi)
    
    return {
        "zone": zone.value,
        "status": status.value,
        "eta_to_port": eta_dt.isoformat() if eta_dt else None,
        "eta_hours": round(eta_hours, 2),
        "eta_confidence": confidence,
    }


# ---------------------------------------------------------------------------
# TESTING
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Test cases
    test_cases = [
        # (lat, lon, sog, description)
        (59.44, 24.75, 0.1, "Old City berth - stationary"),
        (59.50, 24.95, 0.2, "Muuga berth - stationary"),
        (59.50, 24.70, 0.3, "Anchorage - waiting"),
        (59.55, 24.60, 8.5, "Approach - moving"),
        (59.20, 24.30, 10.0, "Outside - far away"),
    ]
    
    print("Zone Classification Test Results:")
    print("-" * 80)
    
    for lat, lon, sog, desc in test_cases:
        result = classify_vessel_position(lat, lon, sog, mmsi="TEST123")
        print(f"\n{desc}:")
        print(f"  Position: ({lat}, {lon}), SOG: {sog} kn")
        print(f"  Zone: {result['zone']}")
        print(f"  Status: {result['status']}")
        print(f"  ETA: {result['eta_hours']} hours ({result['eta_confidence']})")
