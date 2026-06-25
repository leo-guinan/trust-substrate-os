"""Ready-but-blocked offers."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .models import Actor, PredictionReceipt, RoutingKind
from .receipts import make_receipt


@dataclass
class Offer:
    offer_id: str
    credential: str
    kind: str
    issued_at: datetime
    receipt_id: str
    reason: str


def ready_but_blocked_offer(actor: Actor, now: datetime | None = None) -> tuple[Offer, PredictionReceipt]:
    now = now or datetime.utcnow()
    receipt = make_receipt(
        actor.credential,
        RoutingKind.EXISTING_WELL,
        "priority_journeyman_slot",
        "This ready-but-blocked apprentice will remain settled while waiting for or seeding a journeyman path.",
        0.65,
        issued_at=now,
    )
    offer = Offer(
        offer_id="offer_" + receipt.receipt_id.removeprefix("rcpt_"),
        credential=actor.credential,
        kind="priority_journeyman_slot",
        issued_at=now,
        receipt_id=receipt.receipt_id,
        reason="journeyman altitude reached while capacity is full",
    )
    return offer, receipt
