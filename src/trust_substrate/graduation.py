"""Graduation: promotion as a losable prediction receipt."""
from __future__ import annotations

from datetime import datetime

from .capacity import seat_snapshot
from .models import Actor, Gate, GateResult, PredictionReceipt, ReceiptStatus, RoutingKind, SeatPolicy, Tier
from .receipts import make_receipt


def evaluate_graduation_readiness(actor: Actor, receipts: list[PredictionReceipt], policy: SeatPolicy, actors: list[Actor] | None = None) -> GateResult:
    if actor.tier != Tier.APPRENTICE:
        return GateResult(Gate.FIT_MISFIT, False, confidence=0.0, reasoning="not an apprentice")
    settled = [r for r in receipts if r.credential == actor.credential and r.status in {ReceiptStatus.CONFIRMED, ReceiptStatus.DISCONFIRMED}]
    if actor.sigma.lambda_rate < policy.min_lambda_for_graduation:
        return GateResult(Gate.FIT_MISFIT, False, confidence=0.2, reasoning="λ below graduation threshold")
    if actor.sigma.sigma_w > policy.max_sigma_w_for_graduation:
        return GateResult(Gate.FIT_MISFIT, False, confidence=0.3, reasoning="σ_w too high for journeyman altitude")
    if actor.sigma.sigma_s > policy.max_sigma_s_for_graduation:
        return GateResult(Gate.FIT_MISFIT, False, confidence=0.3, reasoning="σ_s too high for journeyman altitude")
    if len(settled) < policy.required_settled_receipts:
        return GateResult(Gate.FIT_MISFIT, False, confidence=0.4, reasoning="not enough settled prediction receipts")
    if actors is not None and seat_snapshot(actors, policy).journeyman_open <= 0:
        return GateResult(Gate.FIT_MISFIT, False, routed_to="_ready_but_blocked", confidence=0.8, reasoning="ready but no journeyman seat open")
    return GateResult(Gate.FIT_MISFIT, True, confidence=0.9, reasoning="σ bounded, λ sufficient, receipts settled")


def graduate_to_journeyman(actor: Actor, policy: SeatPolicy, now: datetime | None = None) -> PredictionReceipt:
    now = now or datetime.utcnow()
    actor.tier = Tier.JOURNEYMAN
    actor.is_trusted = True
    actor.sigma.altitude = max(actor.sigma.altitude, 4)
    return make_receipt(
        credential=actor.credential,
        kind=RoutingKind.GRADUATION,
        predicted_destination="journeyman_orbit",
        prediction="This apprentice will hold journeyman altitude under contact for the next settlement cycle.",
        confidence=0.75,
        issued_at=now,
        settle_after_events=3,
    )
