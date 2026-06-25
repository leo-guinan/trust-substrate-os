"""Satellite factory for artifact pings and reaction triangulation.

A satellite is an instrument deployed at a trust layer. Its job is not to capture
identity; it emits artifacts (tweets, posts, essays, calls) and reads posted
reactions as deformations. This gives a cheap outer-orbit sensor and can also
be deployed deeper in the ladder.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from .models import Actor, EnergyEvent, Outcome, PredictionReceipt, ReceiptStatus, RoutingKind, Tier
from .receipts import make_receipt


class TrustLayer(Enum):
    EDGE = "edge"                 # furthest orbit: public pings / tweets
    VISITOR = "visitor"           # weak contact, no seat
    APPRENTICE = "apprentice"     # apprentice surface
    JOURNEYMAN = "journeyman"     # inner orbit / collaboration
    FEDERATION = "federation"     # cross-well standing recognition


class ArtifactKind(Enum):
    TWEET = "tweet"
    THREAD = "thread"
    ESSAY = "essay"
    DEMO = "demo"
    PROMPT = "prompt"
    OFFER = "offer"


class ReactionKind(Enum):
    VIEW = "view"
    LIKE = "like"
    REPOST = "repost"
    REPLY = "reply"
    QUOTE = "quote"
    CLICK = "click"
    BOOKMARK = "bookmark"
    FOLLOW = "follow"
    APPLY = "apply"
    IGNORE = "ignore"


REACTION_WEIGHTS: dict[ReactionKind, float] = {
    ReactionKind.VIEW: 0.05,
    ReactionKind.LIKE: 0.18,
    ReactionKind.REPOST: 0.45,
    ReactionKind.REPLY: 0.75,
    ReactionKind.QUOTE: 0.9,
    ReactionKind.CLICK: 0.55,
    ReactionKind.BOOKMARK: 0.65,
    ReactionKind.FOLLOW: 0.7,
    ReactionKind.APPLY: 1.0,
    ReactionKind.IGNORE: -0.15,
}

LAYER_ORBITS: dict[TrustLayer, float] = {
    TrustLayer.EDGE: 1.0,
    TrustLayer.VISITOR: 0.82,
    TrustLayer.APPRENTICE: 0.58,
    TrustLayer.JOURNEYMAN: 0.24,
    TrustLayer.FEDERATION: 0.42,
}


@dataclass
class ArtifactPing:
    ping_id: str
    satellite_id: str
    artifact_kind: ArtifactKind
    layer: TrustLayer
    text: str
    target_grain: str
    created_at: datetime
    external_ref: str | None = None      # tweet URL/id, essay URL, etc.
    prediction: str = ""
    receipt_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReactionEvent:
    reaction_id: str
    ping_id: str
    credential: str
    kind: ReactionKind
    timestamp: datetime
    energy: float
    grain_alignment: float
    route_taken: str
    source_ref: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SatelliteDeployment:
    satellite_id: str
    name: str
    layer: TrustLayer
    orbit: float
    purpose: str
    target_grain: str
    deployed_at: datetime
    pings: list[ArtifactPing] = field(default_factory=list)
    reactions: list[ReactionEvent] = field(default_factory=list)


@dataclass
class TriangulationRead:
    credential: str
    estimated_orbit: float
    layer: TrustLayer
    confidence: float
    bearing: dict[str, float]
    evidence_ping_ids: list[str]
    summary: str


def _id(prefix: str, *parts: object) -> str:
    raw = "|".join(str(p) for p in parts)
    return f"{prefix}_{hashlib.sha256(raw.encode()).hexdigest()[:12]}"


def classify_layer(orbit: float) -> TrustLayer:
    if orbit >= 0.9:
        return TrustLayer.EDGE
    if orbit >= 0.68:
        return TrustLayer.VISITOR
    if orbit >= 0.36:
        return TrustLayer.APPRENTICE
    return TrustLayer.JOURNEYMAN


class SatelliteFactory:
    """Deploys satellites and turns reactions into triangulation reads."""

    def __init__(self, well_id: str = "mind_lab"):
        self.well_id = well_id
        self.deployments: dict[str, SatelliteDeployment] = {}
        self.receipts: list[PredictionReceipt] = []

    def deploy(
        self,
        layer: TrustLayer,
        name: str,
        purpose: str,
        target_grain: str,
        deployed_at: datetime | None = None,
    ) -> SatelliteDeployment:
        deployed = deployed_at or datetime.utcnow()
        sat_id = _id("sat", self.well_id, layer.value, name, deployed.isoformat())
        deployment = SatelliteDeployment(
            satellite_id=sat_id,
            name=name,
            layer=layer,
            orbit=LAYER_ORBITS[layer],
            purpose=purpose,
            target_grain=target_grain,
            deployed_at=deployed,
        )
        self.deployments[sat_id] = deployment
        return deployment

    def create_ping(
        self,
        satellite_id: str,
        artifact_kind: ArtifactKind,
        text: str,
        prediction: str,
        external_ref: str | None = None,
        created_at: datetime | None = None,
        settle_after_events: int = 5,
    ) -> ArtifactPing:
        deployment = self.deployments[satellite_id]
        created = created_at or datetime.utcnow()
        ping_id = _id("ping", satellite_id, artifact_kind.value, text, created.isoformat())
        receipt = make_receipt(
            credential=f"satellite:{satellite_id}",
            kind=RoutingKind.EXISTING_WELL,
            predicted_destination=f"layer:{deployment.layer.value}:{deployment.target_grain}",
            prediction=prediction,
            confidence=0.5,
            issued_at=created,
            settle_after_events=settle_after_events,
        )
        self.receipts.append(receipt)
        ping = ArtifactPing(
            ping_id=ping_id,
            satellite_id=satellite_id,
            artifact_kind=artifact_kind,
            layer=deployment.layer,
            text=text,
            target_grain=deployment.target_grain,
            created_at=created,
            external_ref=external_ref,
            prediction=prediction,
            receipt_id=receipt.receipt_id,
        )
        deployment.pings.append(ping)
        return ping

    def record_reaction(
        self,
        ping_id: str,
        credential: str,
        kind: ReactionKind,
        grain_alignment: float,
        route_taken: str,
        timestamp: datetime | None = None,
        source_ref: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ReactionEvent:
        deployment = self._deployment_for_ping(ping_id)
        ts = timestamp or datetime.utcnow()
        weight = REACTION_WEIGHTS[kind]
        energy = max(0.0, weight) * (0.5 + 0.5 * grain_alignment)
        reaction = ReactionEvent(
            reaction_id=_id("react", ping_id, credential, kind.value, ts.isoformat()),
            ping_id=ping_id,
            credential=credential,
            kind=kind,
            timestamp=ts,
            energy=energy,
            grain_alignment=max(0.0, min(1.0, grain_alignment)),
            route_taken=route_taken,
            source_ref=source_ref,
            metadata=metadata or {},
        )
        deployment.reactions.append(reaction)
        return reaction

    def as_energy_event(self, reaction: ReactionEvent) -> EnergyEvent:
        deployment = self._deployment_for_ping(reaction.ping_id)
        return EnergyEvent(
            timestamp=reaction.timestamp,
            energy_spend=reaction.energy,
            zone=f"satellite:{deployment.layer.value}:{deployment.target_grain}",
            route_taken=reaction.route_taken,
            grain_alignment=reaction.grain_alignment,
            outcome=Outcome.COMPLETED if reaction.kind != ReactionKind.IGNORE else Outcome.ABANDONED,
            metadata={"ping_id": reaction.ping_id, "reaction_id": reaction.reaction_id, "reaction_kind": reaction.kind.value},
        )

    def triangulate(self, credential: str, lookback_days: int = 14) -> TriangulationRead:
        cutoff = datetime.utcnow() - timedelta(days=lookback_days)
        reactions = [
            r for d in self.deployments.values() for r in d.reactions
            if r.credential == credential and r.timestamp >= cutoff
        ]
        if not reactions:
            return TriangulationRead(
                credential=credential,
                estimated_orbit=1.0,
                layer=TrustLayer.EDGE,
                confidence=0.0,
                bearing={},
                evidence_ping_ids=[],
                summary="No posted reactions; remains at edge orbit.",
            )
        bearing: dict[str, float] = {}
        weighted_orbit = 0.0
        weight_total = 0.0
        for reaction in reactions:
            deployment = self._deployment_for_ping(reaction.ping_id)
            signed = REACTION_WEIGHTS[reaction.kind] * reaction.grain_alignment
            bearing[deployment.target_grain] = bearing.get(deployment.target_grain, 0.0) + signed
            weight = max(0.05, abs(REACTION_WEIGHTS[reaction.kind]))
            # High-energy aligned reactions pull inward from the deployment layer.
            local_orbit = max(0.02, min(1.0, deployment.orbit - reaction.energy * 0.55))
            weighted_orbit += local_orbit * weight
            weight_total += weight
        estimated_orbit = weighted_orbit / max(weight_total, 1e-9)
        confidence = min(1.0, sum(abs(REACTION_WEIGHTS[r.kind]) for r in reactions) / 4.0)
        strongest = max(bearing.items(), key=lambda kv: kv[1])[0] if bearing else "unknown"
        return TriangulationRead(
            credential=credential,
            estimated_orbit=round(estimated_orbit, 3),
            layer=classify_layer(estimated_orbit),
            confidence=round(confidence, 3),
            bearing={k: round(v, 3) for k, v in sorted(bearing.items(), key=lambda kv: kv[1], reverse=True)},
            evidence_ping_ids=sorted({r.ping_id for r in reactions}),
            summary=f"Strongest bearing: {strongest}; {len(reactions)} posted reactions across satellite pings.",
        )

    def settle_ping_receipts(self) -> list[PredictionReceipt]:
        updated: list[PredictionReceipt] = []
        for receipt in self.receipts:
            sat_id = receipt.credential.removeprefix("satellite:")
            reactions = []
            for deployment in self.deployments.values():
                if deployment.satellite_id != sat_id:
                    continue
                for reaction in deployment.reactions:
                    reactions.append(self.as_energy_event(reaction))
            # Local settlement: enough aligned energy confirms; enough against-grain disconfirms.
            if receipt.status != ReceiptStatus.PENDING:
                updated.append(receipt)
                continue
            relevant = reactions[: receipt.settle_after_events]
            if len(relevant) < receipt.settle_after_events:
                updated.append(receipt)
                continue
            avg = sum(e.grain_alignment for e in relevant) / len(relevant)
            receipt.status = ReceiptStatus.CONFIRMED if avg >= 0.55 else ReceiptStatus.DISCONFIRMED
            receipt.settled_at = max(e.timestamp for e in relevant)
            receipt.settlement_reason = f"satellite reaction alignment avg={avg:.2f} over {len(relevant)} events"
            updated.append(receipt)
        self.receipts = updated
        return updated

    def _deployment_for_ping(self, ping_id: str) -> SatelliteDeployment:
        for deployment in self.deployments.values():
            if any(p.ping_id == ping_id for p in deployment.pings):
                return deployment
        raise KeyError(f"Ping not found: {ping_id}")


def apply_triangulation(actor: Actor, read: TriangulationRead) -> Actor:
    """Blend a satellite read into an actor without capturing identity."""
    actor.current_orbit = round((actor.current_orbit * 0.65) + (read.estimated_orbit * 0.35), 3)
    if read.confidence >= 0.55 and read.layer in {TrustLayer.APPRENTICE, TrustLayer.JOURNEYMAN} and actor.tier == Tier.VISITOR:
        actor.tier = Tier.APPRENTICE
    return actor
