"""Data primitives for the Trust Substrate OS."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


class Gate(Enum):
    DETECTION = 0        # Gate 0: intent or drift?
    FRIEND_FOE = 1       # Gate 1: extractive?
    FIT_MISFIT = 2       # Gate 2: this well's grain?


class Outcome(Enum):
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    LOOPED = "looped"          # tarpit
    REFERRED = "referred"      # wormhole
    EJECTED = "ejected"
    GRADUATED = "graduated"


@dataclass
class EnergyEvent:
    """An impression left on the surface by one actor."""
    timestamp: datetime
    energy_spend: float           # units of non-templatable attention
    zone: str                     # textured zone identifier
    route_taken: str              # branch/path identifier within zone
    grain_alignment: float        # 0.0 (against grain) → 1.0 (with grain)
    outcome: Outcome | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Actor:
    """Path-credential holder. No persistent identity beyond the credential."""
    credential: str               # unforgeable path-credential
    current_orbit: float = 1.0   # 0.0 = surface/core, 1.0 = far/decayed
    energy_history: list[EnergyEvent] = field(default_factory=list)
    gate_passes: list[tuple[Gate, bool, float]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_active: datetime = field(default_factory=datetime.utcnow)
    is_trusted: bool = False     # cleared all gates
    is_ejected: bool = False
    ejected_at: datetime | None = None


@dataclass
class SurfaceTexture:
    """The operator's textured surface definition."""
    well_id: str
    zones: dict[str, ZoneGrain]
    decay_half_life_hours: float = 72.0
    default_grain: float = 0.3


@dataclass
class ZoneGrain:
    """A zone on the textured surface."""
    zone_id: str
    typical_routes: dict[str, float]  # route_id → grain_alignment
    energy_cost_mean: float
    energy_cost_std: float


@dataclass
class GateResult:
    gate: Gate
    passed: bool
    routed_to: str | None = None
    confidence: float = 0.0
    reasoning: str = ""


@dataclass
class OrbitSummary:
    """Summary of an actor's current state for operator inspection."""
    credential: str
    orbit: float
    gate_progress: list[str]       # e.g. ["G0", "G1"]
    recent_deformation: float      # total recent energy
    with_grain_pct: float
    efficiency: float              # lowest-energy path ratio
    divergence: float              # bend toward extraction
    energy_trend: str              # "rising", "steady", "decaying"


# Geometric constants
ORBIT_MIN = 0.0    # surface
ORBIT_MAX = 1.0    # cold/far
ENERGY_SCALE = 10.0  # nominal orbit shift per unit energy
