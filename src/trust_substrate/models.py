"""Data primitives for the Trust Substrate OS."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class Gate(Enum):
    DETECTION = 0        # Gate 0: intent or drift?
    FRIEND_FOE = 1       # Gate 1: extractive?
    FIT_MISFIT = 2       # Gate 2: this well's grain?


class Outcome(Enum):
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    REFERRED = "referred"      # directional route / wormhole legacy language
    EJECTED = "ejected"        # manual override only; automated flow uses receipts
    GRADUATED = "graduated"


class Tier(Enum):
    VISITOR = "visitor"
    APPRENTICE = "apprentice"
    JOURNEYMAN = "journeyman"
    OPERATOR = "operator"


class ReceiptStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    DISCONFIRMED = "disconfirmed"
    EXPIRED = "expired"


class RoutingKind(Enum):
    EXISTING_WELL = "existing_well"
    SYNTHETIC_WELL = "synthetic_well"
    RELEASE_DECAYED = "release_decayed"
    GRADUATION = "graduation"
    REVOCATION_REVIEW = "revocation_review"


class DecisionKind(Enum):
    NEEDS_SIGNAL = "needs_signal"
    APPRENTICE_ACTIVE = "apprentice_active"
    READY_TO_GRADUATE = "ready_to_graduate"
    READY_BUT_BLOCKED = "ready_but_blocked"
    DIRECTIONAL_ROUTE = "directional_route"
    SYNTHESIZE_PROVISIONAL_WELL = "synthesize_provisional_well"
    FLAGGED_TURN = "flagged_turn"
    RELEASE_DECAYED = "release_decayed"


@dataclass
class SigmaState:
    """Current trust-gap read for an identity-free credential."""
    sigma_w: float = 0.0       # prediction vs posted observation
    sigma_s: float = 0.0       # prediction vs model self-coherence
    lambda_rate: float = 0.0   # disconfirmation/settlement cycle rate
    altitude: int = 0          # coarse σ-credential standing
    last_settlement_at: datetime | None = None


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
    current_orbit: float = 1.0    # 0.0 = surface/core, 1.0 = far/decayed
    energy_history: list[EnergyEvent] = field(default_factory=list)
    gate_passes: list[tuple[Gate, bool, float]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_active: datetime = field(default_factory=datetime.utcnow)
    is_trusted: bool = False      # cleared all gates / standing honored here
    is_ejected: bool = False      # manual override only
    ejected_at: datetime | None = None
    tier: Tier = Tier.VISITOR
    sigma: SigmaState = field(default_factory=SigmaState)


@dataclass
class SurfaceTexture:
    """The operator's textured surface definition."""
    well_id: str
    zones: dict[str, "ZoneGrain"]
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
    receipt_id: str | None = None


@dataclass
class PredictionReceipt:
    """A losable prediction emitted by a route, promotion, synthesis, or review."""
    receipt_id: str
    credential: str
    kind: RoutingKind
    predicted_destination: str
    prediction: str
    confidence: float
    issued_at: datetime
    settle_after_events: int = 3
    settle_by: datetime | None = None
    status: ReceiptStatus = ReceiptStatus.PENDING
    settled_at: datetime | None = None
    settlement_reason: str = ""
    evidence_event_ids: list[str] = field(default_factory=list)


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
    sigma_w: float = 0.0
    sigma_s: float = 0.0
    lambda_rate: float = 0.0
    altitude: int = 0


@dataclass
class SeatPolicy:
    apprentice_cap: int = 100
    journeyman_cap: int = 10
    apprentice_release_after_days: int = 30
    min_lambda_for_graduation: float = 0.2
    max_sigma_w_for_graduation: float = 0.35
    max_sigma_s_for_graduation: float = 0.35
    required_settled_receipts: int = 3


@dataclass
class SeatSnapshot:
    apprentice_active: int
    journeyman_active: int
    apprentice_open: int
    journeyman_open: int


@dataclass
class FlowQueueItem:
    credential: str
    decision: DecisionKind
    priority: float
    reason: str
    recommended_action: str
    receipt_id: str | None = None


@dataclass
class WellSignature:
    well_id: str
    name: str
    corpus_id: str
    zone_affinities: dict[str, float]
    altitude_translation: dict[int, int]
    live_link: bool = False
    capacity_hint: int | None = None


@dataclass
class RoutingCandidate:
    well_id: str
    name: str
    score: float
    reason: str
    translated_altitude: int = 0


@dataclass
class ProvisionalWellSpec:
    spec_id: str
    source_credential: str
    generated_from_receipt_id: str
    title: str
    needed_grain: dict[str, float]
    source_corpora: list[str]
    confidence: float
    status: ReceiptStatus = ReceiptStatus.PENDING


@dataclass
class ProductPrediction:
    id: str
    claim: str
    null: str
    metric: str
    control_window: str
    falsifier: str
    status: ReceiptStatus = ReceiptStatus.PENDING
    evidence: list[str] = field(default_factory=list)


# Geometric constants
ORBIT_MIN = 0.0    # surface
ORBIT_MAX = 1.0    # cold/far
ENERGY_SCALE = 10.0  # nominal orbit shift per unit energy
