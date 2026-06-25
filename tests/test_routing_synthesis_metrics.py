"""Tests for routing, synthesis, metrics, and predictions."""
from datetime import datetime

from trust_substrate.models import Actor, EnergyEvent, ReceiptStatus, RoutingKind
from trust_substrate.receipts import make_receipt, settle_receipt
from trust_substrate.routing import default_wells, rank_destinations
from trust_substrate.surfaces import mind_lab_surface
from trust_substrate.synthesis import synthesize_well
from trust_substrate.metrics import dashboard_metrics
from trust_substrate.predictions import prediction_registry


def test_rank_destinations_returns_named_wells():
    actor = Actor("c")
    actor.energy_history.append(EnergyEvent(datetime.utcnow(), 2.0, "application", "specific_case_analysis", 0.85))
    ranked = rank_destinations(actor, mind_lab_surface(), default_wells())
    assert ranked
    assert ranked[0].well_id.startswith("well_")
    assert 0 <= ranked[0].score <= 1


def test_synthesize_well_starts_pending_and_low_confidence():
    now = datetime.utcnow()
    actor = Actor("c")
    actor.energy_history.append(EnergyEvent(now, 2.0, "application", "off_grain", 0.2))
    receipt = make_receipt("c", RoutingKind.SYNTHETIC_WELL, "synthetic", "need new well", 0.8, now)
    spec = synthesize_well(actor, receipt, ["mind_lab"])
    assert spec.status == ReceiptStatus.PENDING
    assert spec.confidence <= 0.45
    assert "application" in spec.needed_grain


def test_metrics_and_prediction_registry_have_falsifiers():
    now = datetime.utcnow()
    actor = Actor("c")
    receipt = make_receipt("c", RoutingKind.SYNTHETIC_WELL, "synthetic", "x", 0.5, now, settle_after_events=1)
    receipt = settle_receipt(receipt, [EnergyEvent(now, 1.0, "synthetic", "land", 0.8)], now)
    metrics = dashboard_metrics([actor], [receipt])
    assert metrics["receipt_settlement_rate"] == 1.0
    preds = prediction_registry()
    assert len(preds) == 5
    assert all(p.falsifier for p in preds)
