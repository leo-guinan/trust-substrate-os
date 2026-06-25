"""Prediction receipts: losable claims with settlement rules."""
from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import datetime

from .models import EnergyEvent, PredictionReceipt, ReceiptStatus, RoutingKind


def _receipt_id(credential: str, kind: RoutingKind, destination: str, issued_at: datetime) -> str:
    raw = f"{credential}|{kind.value}|{destination}|{issued_at.isoformat()}".encode()
    return "rcpt_" + hashlib.sha256(raw).hexdigest()[:12]


def make_receipt(
    credential: str,
    kind: RoutingKind,
    predicted_destination: str,
    prediction: str,
    confidence: float,
    issued_at: datetime | None = None,
    settle_after_events: int = 3,
) -> PredictionReceipt:
    issued = issued_at or datetime.utcnow()
    return PredictionReceipt(
        receipt_id=_receipt_id(credential, kind, predicted_destination, issued),
        credential=credential,
        kind=kind,
        predicted_destination=predicted_destination,
        prediction=prediction,
        confidence=max(0.0, min(1.0, confidence)),
        issued_at=issued,
        settle_after_events=settle_after_events,
    )


def settlement_events(receipt: PredictionReceipt, events: list[EnergyEvent]) -> list[EnergyEvent]:
    dest = receipt.predicted_destination
    post = [e for e in events if e.timestamp >= receipt.issued_at]
    if dest and not dest.startswith("_"):
        routed = [e for e in post if e.metadata.get("destination") == dest or e.zone == dest]
        if routed:
            return routed
    return post


def settle_receipt(receipt: PredictionReceipt, events: list[EnergyEvent], now: datetime | None = None) -> PredictionReceipt:
    """Settle a receipt from posted events. No hidden type inference."""
    if receipt.status != ReceiptStatus.PENDING:
        return receipt
    now = now or datetime.utcnow()
    if receipt.settle_by and now > receipt.settle_by:
        return replace(receipt, status=ReceiptStatus.EXPIRED, settled_at=now, settlement_reason="settlement window expired")

    evs = settlement_events(receipt, events)
    if len(evs) < receipt.settle_after_events:
        return receipt

    mean_grain = sum(e.grain_alignment for e in evs) / len(evs)
    evidence_ids = [str(e.metadata.get("event_id", f"event_{i}")) for i, e in enumerate(evs)]
    if mean_grain >= 0.55:
        return replace(
            receipt,
            status=ReceiptStatus.CONFIRMED,
            settled_at=now,
            settlement_reason=f"mean posted grain {mean_grain:.2f} confirmed prediction",
            evidence_event_ids=evidence_ids,
        )
    if mean_grain <= 0.35:
        return replace(
            receipt,
            status=ReceiptStatus.DISCONFIRMED,
            settled_at=now,
            settlement_reason=f"mean posted grain {mean_grain:.2f} disconfirmed prediction",
            evidence_event_ids=evidence_ids,
        )
    return receipt


def settled_count(receipts: list[PredictionReceipt], credential: str | None = None) -> int:
    return sum(
        1
        for r in receipts
        if r.status in {ReceiptStatus.CONFIRMED, ReceiptStatus.DISCONFIRMED}
        and (credential is None or r.credential == credential)
    )
