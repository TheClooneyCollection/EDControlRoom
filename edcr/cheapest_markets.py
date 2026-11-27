"""Cheapest markets for a commodity: hub store query merged with Spansh rows."""

from __future__ import annotations

from dataclasses import dataclass

PAD_ORDER = {"S": 1, "M": 2, "L": 3}


@dataclass(frozen=True)
class CheapestQuery:
    commodity: str  # EDDN symbol, lower case: "tritium"
    reference_system: str  # "" = no distance column and no radius
    radius_ly: float | None  # None = galaxy-wide
    min_supply: int
    pad: str  # "S" | "M" | "L": the smallest pad the ship can use
    max_age_hours: float
    include_carriers: bool
    use_spansh: bool
    limit: int  # 50


@dataclass(frozen=True)
class MarketOffer:
    source: str  # "hub" | "spansh"
    market_id: int
    system_name: str
    station_name: str
    station_type: str  # "" when unknown
    is_carrier: bool
    max_pad: str  # "S" | "M" | "L" | "" unknown
    dist_ls: float | None
    distance_ly: float | None  # None when no reference system
    buy_price: int
    supply: int
    updated_at: float  # epoch seconds
    suspect_price: bool  # carrier price under 10% of the station median
