"""Tests for satellite factory triangulation."""
from datetime import datetime

from trust_substrate import Actor
from trust_substrate.satellites import (
    ArtifactKind,
    ReactionKind,
    SatelliteFactory,
    TrustLayer,
    apply_triangulation,
)


def test_deploys_satellite_to_any_trust_layer():
    factory = SatelliteFactory("mind_lab")
    edge = factory.deploy(TrustLayer.EDGE, "edge", "public tweet pings", "shape_of_trust")
    app = factory.deploy(TrustLayer.APPRENTICE, "app", "apprentice artifacts", "application")
    jour = factory.deploy(TrustLayer.JOURNEYMAN, "jour", "inner orbit artifacts", "well_design")
    assert edge.orbit > app.orbit > jour.orbit
    assert edge.layer == TrustLayer.EDGE


def test_ping_issues_receipt_and_reactions_settle_it():
    now = datetime.utcnow()
    factory = SatelliteFactory("mind_lab")
    sat = factory.deploy(TrustLayer.EDGE, "edge", "tweets", "shape_of_trust", now)
    ping = factory.create_ping(sat.satellite_id, ArtifactKind.TWEET, "claim", "reactions will align", "tweet://1", now, settle_after_events=2)
    assert ping.receipt_id is not None
    factory.record_reaction(ping.ping_id, "cred_a", ReactionKind.REPLY, 0.8, "asks_schema", now)
    factory.record_reaction(ping.ping_id, "cred_b", ReactionKind.BOOKMARK, 0.7, "saves", now)
    receipts = factory.settle_ping_receipts()
    assert receipts[0].status.value == "confirmed"
    assert "alignment" in receipts[0].settlement_reason


def test_triangulates_position_from_cross_layer_reactions():
    now = datetime.utcnow()
    factory = SatelliteFactory("mind_lab")
    edge = factory.deploy(TrustLayer.EDGE, "edge", "tweets", "shape_of_trust", now)
    app = factory.deploy(TrustLayer.APPRENTICE, "app", "demo", "application", now)
    p1 = factory.create_ping(edge.satellite_id, ArtifactKind.TWEET, "claim", "edge read", created_at=now)
    p2 = factory.create_ping(app.satellite_id, ArtifactKind.DEMO, "dashboard", "app read", created_at=now)
    factory.record_reaction(p1.ping_id, "cred_a", ReactionKind.REPLY, 0.8, "asks_schema", now)
    factory.record_reaction(p2.ping_id, "cred_a", ReactionKind.APPLY, 0.9, "posts_case", now)
    read = factory.triangulate("cred_a")
    assert read.confidence > 0.4
    assert read.estimated_orbit < 1.0
    assert "application" in read.bearing


def test_apply_triangulation_moves_actor_without_identity_capture():
    factory = SatelliteFactory("mind_lab")
    sat = factory.deploy(TrustLayer.APPRENTICE, "app", "demo", "application")
    ping = factory.create_ping(sat.satellite_id, ArtifactKind.DEMO, "dashboard", "readiness")
    factory.record_reaction(ping.ping_id, "cred_a", ReactionKind.APPLY, 0.9, "posts_case")
    read = factory.triangulate("cred_a")
    actor = Actor("cred_a")
    before = actor.current_orbit
    apply_triangulation(actor, read)
    assert actor.current_orbit < before
    assert actor.credential == "cred_a"
