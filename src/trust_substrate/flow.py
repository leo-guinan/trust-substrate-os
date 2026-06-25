"""Apprentice → journeyman graduation flow queue."""
from __future__ import annotations

from datetime import datetime, timedelta

from .capacity import seat_snapshot
from .models import Actor, DecisionKind, FlowQueueItem, PredictionReceipt, ReceiptStatus, RoutingKind, SeatPolicy, Tier


def _has_pending(actor: Actor, receipts: list[PredictionReceipt], kind: RoutingKind | None = None) -> PredictionReceipt | None:
    for r in receipts:
        if r.credential != actor.credential or r.status != ReceiptStatus.PENDING:
            continue
        if kind is None or r.kind == kind:
            return r
    return None


def _settled_receipts(actor: Actor, receipts: list[PredictionReceipt]) -> int:
    return sum(1 for r in receipts if r.credential == actor.credential and r.status in {ReceiptStatus.CONFIRMED, ReceiptStatus.DISCONFIRMED})


def build_flow_queue(
    actors: list[Actor],
    receipts: list[PredictionReceipt],
    policy: SeatPolicy,
    now: datetime | None = None,
) -> list[FlowQueueItem]:
    now = now or datetime.utcnow()
    snap = seat_snapshot(actors, policy)
    items: list[FlowQueueItem] = []
    for actor in actors:
        pending_revocation = _has_pending(actor, receipts, RoutingKind.REVOCATION_REVIEW)
        if pending_revocation:
            items.append(FlowQueueItem(actor.credential, DecisionKind.FLAGGED_TURN, 1.0, "pending turn review receipt", "observe next posted events before revocation", pending_revocation.receipt_id))
            continue

        age_since_active = now - actor.last_active
        if actor.tier == Tier.APPRENTICE and age_since_active > timedelta(days=policy.apprentice_release_after_days):
            items.append(FlowQueueItem(actor.credential, DecisionKind.RELEASE_DECAYED, 0.9, "apprentice contact decayed past release horizon", "release or route with receipt"))
            continue

        ready = (
            actor.tier == Tier.APPRENTICE
            and actor.sigma.sigma_w <= policy.max_sigma_w_for_graduation
            and actor.sigma.sigma_s <= policy.max_sigma_s_for_graduation
            and actor.sigma.lambda_rate >= policy.min_lambda_for_graduation
            and _settled_receipts(actor, receipts) >= policy.required_settled_receipts
        )
        if ready and snap.journeyman_open > 0:
            items.append(FlowQueueItem(actor.credential, DecisionKind.READY_TO_GRADUATE, 0.95, "σ bounded and λ sufficient; journeyman seat open", "issue graduation receipt"))
            continue
        if ready:
            items.append(FlowQueueItem(actor.credential, DecisionKind.READY_BUT_BLOCKED, 0.92, "ready but no journeyman seat open", "offer priority slot or seed own well"))
            continue

        pending_route = _has_pending(actor, receipts, RoutingKind.EXISTING_WELL)
        if pending_route:
            items.append(FlowQueueItem(actor.credential, DecisionKind.DIRECTIONAL_ROUTE, 0.8, "existing-well routing receipt pending", "watch settlement at destination", pending_route.receipt_id))
            continue

        pending_synth = _has_pending(actor, receipts, RoutingKind.SYNTHETIC_WELL)
        if pending_synth:
            items.append(FlowQueueItem(actor.credential, DecisionKind.SYNTHESIZE_PROVISIONAL_WELL, 0.78, "synthetic well receipt pending", "validate provisional destination at λ", pending_synth.receipt_id))
            continue

        meaningful = [e for e in actor.energy_history if e.energy_spend >= 1.0]
        if len(meaningful) < 2:
            items.append(FlowQueueItem(actor.credential, DecisionKind.NEEDS_SIGNAL, 0.3, "not enough posted energy to classify", "ask for contextual costly signal"))
            continue

        items.append(FlowQueueItem(actor.credential, DecisionKind.APPRENTICE_ACTIVE, 0.5, "active but not graduation-ready", "continue textured apprentice surface"))

    return sorted(items, key=lambda i: i.priority, reverse=True)
