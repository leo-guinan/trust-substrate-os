"""Fake satellite deployments and reaction reads for UI demos."""
from __future__ import annotations

from datetime import datetime, timedelta

from .satellites import ArtifactKind, ReactionKind, SatelliteFactory, TrustLayer


def fake_satellite_factory() -> SatelliteFactory:
    factory = SatelliteFactory("mind_lab")
    now = datetime.utcnow()
    edge = factory.deploy(
        TrustLayer.EDGE,
        "Furthest Edge Tweet Listener",
        "Track reactions to public tweets/pings before identity capture.",
        "shape_of_trust",
        now - timedelta(days=2),
    )
    app = factory.deploy(
        TrustLayer.APPRENTICE,
        "Apprentice Artifact Echo",
        "Measure who reacts to apprentice-created artifacts with usable specificity.",
        "application",
        now - timedelta(days=1),
    )
    jour = factory.deploy(
        TrustLayer.JOURNEYMAN,
        "Journeyman Collaboration Probe",
        "Measure high-altitude reactions to deeper collaboration artifacts.",
        "well_design",
        now - timedelta(hours=12),
    )
    p1 = factory.create_ping(
        edge.satellite_id,
        ArtifactKind.TWEET,
        "Trust is the gap you keep open long enough to score.",
        "Public reactions will separate passive agreement from artifact-seeking intent.",
        "https://x.com/example/status/1001",
        now - timedelta(days=2),
    )
    p2 = factory.create_ping(
        edge.satellite_id,
        ArtifactKind.THREAD,
        "A rejection without a receipt teaches the membrane nothing.",
        "Replies and bookmarks will reveal builders who understand losable routing.",
        "https://x.com/example/status/1002",
        now - timedelta(days=1, hours=20),
    )
    p3 = factory.create_ping(
        app.satellite_id,
        ArtifactKind.DEMO,
        "Apprentice flow dashboard snapshot",
        "Specific clicks and replies reveal readiness to apply the lens.",
        "docs/apprentice-flow.html",
        now - timedelta(days=1),
    )
    p4 = factory.create_ping(
        jour.satellite_id,
        ArtifactKind.PROMPT,
        "Design your own well from three prediction receipts.",
        "High-resolution responses reveal journeyman-grade well design orientation.",
        None,
        now - timedelta(hours=12),
    )
    # Same pseudonymous credentials reacting across layers = triangulation, not identity capture.
    factory.record_reaction(p1.ping_id, "cred_000", ReactionKind.LIKE, 0.55, "recognition", now - timedelta(days=2, minutes=5))
    factory.record_reaction(p2.ping_id, "cred_000", ReactionKind.REPLY, 0.82, "asks_for_receipt_schema", now - timedelta(days=1, hours=18))
    factory.record_reaction(p3.ping_id, "cred_000", ReactionKind.CLICK, 0.78, "opens_flow_queue", now - timedelta(hours=20))
    factory.record_reaction(p1.ping_id, "cred_007", ReactionKind.REPOST, 0.42, "generic_agreement", now - timedelta(days=1, hours=23))
    factory.record_reaction(p2.ping_id, "cred_007", ReactionKind.IGNORE, 0.1, "no_followthrough", now - timedelta(days=1, hours=10))
    factory.record_reaction(p1.ping_id, "cred_014", ReactionKind.QUOTE, 0.88, "applies_to_own_system", now - timedelta(days=1, hours=22))
    factory.record_reaction(p3.ping_id, "cred_014", ReactionKind.BOOKMARK, 0.8, "saves_dashboard", now - timedelta(hours=18))
    factory.record_reaction(p4.ping_id, "cred_014", ReactionKind.REPLY, 0.9, "submits_well_spec", now - timedelta(hours=10))
    factory.record_reaction(p1.ping_id, "cred_021", ReactionKind.VIEW, 0.2, "scroll_past", now - timedelta(days=1, hours=21))
    factory.record_reaction(p2.ping_id, "cred_021", ReactionKind.LIKE, 0.25, "low_context_like", now - timedelta(days=1, hours=19))
    factory.record_reaction(p3.ping_id, "cred_028", ReactionKind.APPLY, 0.92, "posts_case_note", now - timedelta(hours=16))
    factory.record_reaction(p4.ping_id, "cred_028", ReactionKind.REPLY, 0.86, "designs_satellite", now - timedelta(hours=8))
    factory.settle_ping_receipts()
    return factory
