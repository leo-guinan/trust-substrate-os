"""Tests for σ-flow additions."""
from datetime import datetime, timedelta

from trust_substrate import Actor, EnergyEvent, Outcome, ReceiptStatus, RoutingKind, SeatPolicy, Tier, make_receipt, settle_receipt
from trust_substrate.capacity import seat_snapshot
from trust_substrate.flow import build_flow_queue
from trust_substrate.graduation import evaluate_graduation_readiness, graduate_to_journeyman
from trust_substrate.models import DecisionKind
from trust_substrate.sigma import SigmaEngine


def test_no_tarpit_outcome_is_emitted_by_domain_model():
    assert "LOOPED" not in Outcome.__members__


def test_actor_starts_with_bounded_empty_sigma_state():
    actor = Actor(credential="cred_x")
    assert actor.tier == Tier.VISITOR
    assert actor.sigma.sigma_w == 0.0
    assert actor.sigma.sigma_s == 0.0
    assert actor.sigma.lambda_rate == 0.0
    assert actor.sigma.altitude == 0


def test_receipt_settlement_confirm_and_disconfirm():
    now = datetime.utcnow()
    receipt = make_receipt("c", RoutingKind.EXISTING_WELL, "well_a", "belongs there", 0.7, now, settle_after_events=2)
    events = [
        EnergyEvent(now + timedelta(minutes=1), 1.0, "well_a", "land", 0.8),
        EnergyEvent(now + timedelta(minutes=2), 1.0, "well_a", "land", 0.7),
    ]
    assert settle_receipt(receipt, events).status == ReceiptStatus.CONFIRMED
    bad = [EnergyEvent(now + timedelta(minutes=1), 1.0, "well_a", "land", 0.1), EnergyEvent(now + timedelta(minutes=2), 1.0, "well_a", "land", 0.2)]
    assert settle_receipt(receipt, bad).status == ReceiptStatus.DISCONFIRMED


def test_sigma_lambda_only_grows_from_settled_receipts():
    now = datetime.utcnow()
    actor = Actor("c", tier=Tier.APPRENTICE)
    actor.energy_history.append(EnergyEvent(now, 2.0, "application", "specific", 0.8))
    pending = make_receipt("c", RoutingKind.EXISTING_WELL, "x", "pending", 0.5, now)
    sigma = SigmaEngine().update_actor_sigma(actor, [pending], now)
    assert sigma.lambda_rate == 0.0
    confirmed = settle_receipt(pending, [
        EnergyEvent(now, 1, "x", "a", 0.9),
        EnergyEvent(now, 1, "x", "a", 0.9),
        EnergyEvent(now, 1, "x", "a", 0.9),
    ], now)
    sigma = SigmaEngine().update_actor_sigma(actor, [confirmed], now)
    assert sigma.lambda_rate > 0.0


def test_capacity_snapshot_counts_seats():
    policy = SeatPolicy(apprentice_cap=2, journeyman_cap=1)
    actors = [Actor("a", tier=Tier.APPRENTICE), Actor("b", tier=Tier.JOURNEYMAN)]
    snap = seat_snapshot(actors, policy)
    assert snap.apprentice_open == 1
    assert snap.journeyman_open == 0


def test_graduation_requires_lambda_and_receipts():
    actor = Actor("a", tier=Tier.APPRENTICE)
    actor.sigma.sigma_w = 0.2
    actor.sigma.sigma_s = 0.2
    actor.sigma.lambda_rate = 1.5
    now = datetime.utcnow()
    receipts = []
    for i in range(3):
        r = make_receipt("a", RoutingKind.EXISTING_WELL, "mind_lab", "ok", 0.7, now, settle_after_events=1)
        receipts.append(settle_receipt(r, [EnergyEvent(now, 1, "mind_lab", "ok", 0.8)], now))
    assert evaluate_graduation_readiness(actor, receipts, SeatPolicy()).passed is True
    grad = graduate_to_journeyman(actor, SeatPolicy(), now)
    assert actor.tier == Tier.JOURNEYMAN
    assert grad.kind == RoutingKind.GRADUATION


def test_flow_queue_marks_ready_to_graduate():
    actor = Actor("a", tier=Tier.APPRENTICE)
    actor.sigma.sigma_w = 0.2
    actor.sigma.sigma_s = 0.2
    actor.sigma.lambda_rate = 1.5
    now = datetime.utcnow()
    receipts = []
    for i in range(3):
        r = make_receipt("a", RoutingKind.EXISTING_WELL, "mind_lab", "ok", 0.7, now, settle_after_events=1)
        receipts.append(settle_receipt(r, [EnergyEvent(now, 1, "mind_lab", "ok", 0.8)], now))
    queue = build_flow_queue([actor], receipts, SeatPolicy())
    assert queue[0].decision == DecisionKind.READY_TO_GRADUATE
