"""Fit the trip time model per ship from the journal event store (plan 0016).

A leg runs from `Undocked` to the next `Docked` on one node; a docked stop from `Docked` to the
next `Undocked`. Each belongs to the `ShipID` of the latest `Loadout` or `LoadGame` before it.
"""
from __future__ import annotations

import sqlite3
import statistics
import threading
from dataclasses import asdict, dataclass, replace
from typing import Any, Callable, Iterable

from edcr.eddn.routes import SURFACE_TYPES, TimeModel

# Fitted by least squares on the legs; `docked_s` is the median stop.
LEG_FIELDS = ("travel_base_s", "first_jump_s", "per_extra_jump_s", "supercruise_coeff", "surface_extra_s")
# Any of these inside a leg means it was not a plain flight.
BROKEN_BY = frozenset({"Died", "Interdicted", "EscapeInterdiction", "Touchdown", "Shutdown", "LoadGame", "Resurrect"})
MAX_LEG_S = 1800.0
MAX_STOP_S = 600.0
# A field with fewer supporting legs (stops for `docked_s`) keeps its configured value.
MIN_FIELD_SUPPORT = 10
# Fewer legs for a ship fits the pooled legs of every ship; fewer pooled legs keeps the configured model.
MIN_LEGS = 30
REFRESH_S = 60.0
_EVENTS = ("Undocked", "Docked", "FSDJump", "SupercruiseExit", "Loadout", *sorted(BROKEN_BY))
# A tiny pull towards the configured values, so legs that leave a field undetermined cannot make the fit singular.
_RIDGE = 1e-6


@dataclass(frozen=True)
class Leg:
    ship_id: int | None
    seconds: float
    jumps: int
    dist_ls: float | None
    surface: bool


@dataclass(frozen=True)
class Stop:
    ship_id: int | None
    seconds: float


@dataclass(frozen=True)
class TimeModelFit:
    # "ship" for the ship's own legs, "pooled" for every ship's, "config" when there were too few legs.
    scope: str
    ship_id: int | None
    model: TimeModel
    legs: int
    stops: int
    # Fields the legs fitted; the rest kept the configured value.
    fitted: tuple[str, ...]
    # Supporting legs (stops for `docked_s`) per field.
    support: dict[str, int]


def read_legs(db: sqlite3.Connection, since: float) -> tuple[list[Leg], list[Stop]]:
    """Legs and docked stops after `since` (epoch seconds) on every node of the store."""
    marks = ",".join("?" for _ in _EVENTS)
    rows = db.execute(
        f"SELECT node_id, timestamp, event, json_extract(body, '$.ShipID'), json_extract(body, '$.DistFromStarLS'),"
        f" json_extract(body, '$.StationType') FROM journal_event WHERE event IN ({marks})"
        # The ship flown at `since` comes from an earlier Loadout or LoadGame.
        " AND (timestamp >= ? OR event IN ('Loadout', 'LoadGame')) ORDER BY node_id, file, line",
        (*_EVENTS, since),
    )
    legs: list[Leg] = []
    stops: list[Stop] = []
    node = None
    ship: int | None = None
    leg: dict[str, Any] | None = None
    docked_at: float | None = None
    for node_id, at, event, ship_id, dist_ls, station_type in rows:
        if node_id != node:
            node, ship, leg, docked_at = node_id, None, None, None
        if event in ("Loadout", "LoadGame"):
            ship = ship_id if isinstance(ship_id, int) else None
            if event == "LoadGame":
                leg, docked_at = None, None
            continue
        if at < since:
            continue
        if event == "Undocked":
            if docked_at is not None and at - docked_at <= MAX_STOP_S:
                stops.append(Stop(ship, at - docked_at))
            leg, docked_at = {"at": at, "ship": ship, "jumps": 0, "exits": 0, "broken": False}, None
        elif event == "Docked":
            if leg is not None and not leg["broken"] and leg["exits"] <= 1 and at - leg["at"] <= MAX_LEG_S:
                dist = float(dist_ls) if isinstance(dist_ls, (int, float)) else None
                legs.append(Leg(leg["ship"], at - leg["at"], leg["jumps"], dist, station_type in SURFACE_TYPES))
            leg, docked_at = None, at
        elif leg is not None:
            if event == "FSDJump":
                leg["jumps"] += 1
            elif event == "SupercruiseExit":
                leg["exits"] += 1
            elif event in BROKEN_BY:
                leg["broken"] = True
        if event in BROKEN_BY:
            docked_at = None
    return legs, stops


def _columns(leg: Leg, configured: TimeModel) -> dict[str, float]:
    distance = configured.unknown_dist_ls if leg.dist_ls is None else max(0.0, leg.dist_ls)
    return {
        "travel_base_s": 1.0,
        "first_jump_s": 1.0 if leg.jumps > 0 else 0.0,
        "per_extra_jump_s": float(max(0, leg.jumps - 1)),
        "supercruise_coeff": distance ** (1 / 3),
        "surface_extra_s": 1.0 if leg.surface else 0.0,
    }


def leg_support(legs: Iterable[Leg]) -> dict[str, int]:
    """Legs that tell each field apart: `travel_base_s` needs legs without a jump to split it from
    `first_jump_s`."""
    support = dict.fromkeys(LEG_FIELDS, 0)
    for leg in legs:
        support["travel_base_s"] += leg.jumps == 0
        support["first_jump_s"] += leg.jumps > 0
        support["per_extra_jump_s"] += leg.jumps > 1
        support["supercruise_coeff"] += leg.dist_ls is not None
        support["surface_extra_s"] += leg.surface
    return support


def _solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    """Gaussian elimination with partial pivoting; the ridge keeps the matrix regular."""
    size = len(vector)
    rows = [matrix[i][:] + [vector[i]] for i in range(size)]
    for col in range(size):
        pivot = max(range(col, size), key=lambda r: abs(rows[r][col]))
        rows[col], rows[pivot] = rows[pivot], rows[col]
        for r in range(size):
            if r != col:
                factor = rows[r][col] / rows[col][col]
                rows[r] = [a - factor * b for a, b in zip(rows[r], rows[col])]
    return [rows[i][size] / rows[i][i] for i in range(size)]


def _least_squares(legs: list[Leg], configured: TimeModel, free: tuple[str, ...]) -> dict[str, float]:
    """The free fields fitted to the legs, with the other fields held at their configured value."""
    fixed = [name for name in LEG_FIELDS if name not in free]
    xs, ys = [], []
    for leg in legs:
        columns = _columns(leg, configured)
        xs.append([columns[name] for name in free])
        ys.append(leg.seconds - sum(columns[name] * getattr(configured, name) for name in fixed))
    prior = [getattr(configured, name) for name in free]
    matrix = [[sum(x[i] * x[j] for x in xs) + (_RIDGE if i == j else 0.0) for j in range(len(free))]
              for i in range(len(free))]
    vector = [sum(x[i] * y for x, y in zip(xs, ys)) + _RIDGE * prior[i] for i in range(len(free))]
    return dict(zip(free, _solve(matrix, vector)))


def _residuals(legs: list[Leg], model: TimeModel) -> list[float]:
    return [leg.seconds - sum(value * getattr(model, name) for name, value in _columns(leg, model).items())
            for leg in legs]


def fit_legs(legs: list[Leg], stops: list[Stop], configured: TimeModel) -> tuple[TimeModel, tuple[str, ...], dict[str, int], int]:
    """Fit once, drop legs off by more than max(60s, 3 robust sigma), fit again.

    Returns the model, the fitted fields, their support and the legs kept.
    """
    support = {**leg_support(legs), "docked_s": len(stops)}
    free = tuple(name for name in LEG_FIELDS if support[name] >= MIN_FIELD_SUPPORT)
    model = configured
    kept = legs
    if free:
        model = replace(configured, **_least_squares(legs, configured, free))
        residuals = _residuals(legs, model)
        sigma = 1.4826 * statistics.median(abs(r) for r in residuals)
        kept = [leg for leg, r in zip(legs, residuals) if abs(r) <= max(60.0, 3 * sigma)]
        if kept and len(kept) < len(legs):
            model = replace(configured, **_least_squares(kept, configured, free))
    if support["docked_s"] >= MIN_FIELD_SUPPORT:
        model = replace(model, docked_s=statistics.median(stop.seconds for stop in stops))
        free = ("docked_s", *free)
    model = replace(model, **{name: max(0.0, getattr(model, name)) for name in free})
    return model, free, support, len(kept)


def fit_ships(legs: list[Leg], stops: list[Stop], configured: TimeModel) -> dict[int | None, TimeModelFit]:
    """Each ship with enough legs under its ShipID, and the pooled fit under None (scope "config" when
    there are too few legs for any)."""
    fits: dict[int | None, TimeModelFit] = {}
    if len(legs) >= MIN_LEGS:
        model, fitted, support, kept = fit_legs(legs, stops, configured)
        fits[None] = TimeModelFit("pooled", None, model, kept, len(stops), fitted, support)
    else:
        fits[None] = TimeModelFit("config", None, configured, len(legs), len(stops), (), {})
    for ship_id in {leg.ship_id for leg in legs if leg.ship_id is not None}:
        own = [leg for leg in legs if leg.ship_id == ship_id]
        if len(own) < MIN_LEGS:
            continue
        own_stops = [stop for stop in stops if stop.ship_id == ship_id]
        model, fitted, support, kept = fit_legs(own, own_stops, configured)
        fits[ship_id] = TimeModelFit("ship", ship_id, model, kept, len(own_stops), fitted, support)
    return fits


def fit_payload(fit: TimeModelFit) -> dict[str, Any]:
    return {**asdict(fit), "fitted": list(fit.fitted)}


class TripTimeModels:
    """The trip time model in use: the configured one, or with `source = "fitted"` the one fitted for
    the ship. Fits read the journal store at most once every `REFRESH_S`."""

    def __init__(
        self,
        *,
        configured: TimeModel,
        source: str,
        fit_days: float,
        connect: Callable[[], sqlite3.Connection] | None,
        clock: Callable[[], float],
    ) -> None:
        self.configured = configured
        self.source = source
        self.fit_days = fit_days
        # None on a peer, whose hub keeps the journal events.
        self._connect = connect
        self._clock = clock
        self._lock = threading.Lock()
        self._fits: dict[int | None, TimeModelFit] | None = None
        self._fitted_at = 0.0

    def set_configured(self, configured: TimeModel, source: str) -> None:
        with self._lock:
            self.configured, self.source = configured, source
            self._fits = None

    def fits(self) -> dict[int | None, TimeModelFit]:
        now = self._clock()
        with self._lock:
            if self._fits is None or now - self._fitted_at >= REFRESH_S:
                self._fits = self._fit(now)
                self._fitted_at = now
            return self._fits

    def _fit(self, now: float) -> dict[int | None, TimeModelFit]:
        if self._connect is None:
            return {None: TimeModelFit("config", None, self.configured, 0, 0, (), {})}
        try:
            db = self._connect()
            try:
                legs, stops = read_legs(db, now - self.fit_days * 86400)
            finally:
                db.close()
        except sqlite3.Error:
            legs, stops = [], []
        return fit_ships(legs, stops, self.configured)

    def fitted_for(self, ship_id: int | None) -> TimeModelFit:
        """The ship's own fit, else the pooled one, else the configured model."""
        fits = self.fits()
        return fits.get(ship_id) or fits[None]

    def active(self, ship_id: int | None) -> TimeModelFit:
        if self.source != "fitted":
            return TimeModelFit("config", None, self.configured, 0, 0, (), {})
        return self.fitted_for(ship_id)

    def payload(self, ship_id: int | None) -> dict[str, Any]:
        """Both sets and which is in use, for `/api/time-model` and the trip time's source line."""
        fitted = self.fitted_for(ship_id)
        return {
            "source": self.source,
            "fit_days": self.fit_days,
            "ship_id": ship_id,
            "configured": asdict(self.configured),
            "fitted": fit_payload(fitted),
            "active": fit_payload(self.active(ship_id)),
        }


def model_from_payload(body: Any) -> TimeModel | None:
    """The model of a `fit_payload`, as a peer gets it from the hub, or None when it is not one."""
    try:
        return TimeModel(**{name: float(body["model"][name]) for name in TimeModel.__dataclass_fields__})
    except (KeyError, TypeError, ValueError):
        return None


def connect_read_only(path: Any) -> Callable[[], sqlite3.Connection]:
    return lambda: sqlite3.connect(f"file:{path}?mode=ro", uri=True)

