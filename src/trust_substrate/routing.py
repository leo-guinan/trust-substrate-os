"""Federated directional routing."""
from __future__ import annotations

from .models import Actor, RoutingCandidate, SurfaceTexture, WellSignature


def default_wells() -> list[WellSignature]:
    return [
        WellSignature("well_builder", "Builder Well", "mind_lab", {"application": 0.9, "well_design": 0.85}, {0: 0, 1: 1, 2: 2, 3: 2}),
        WellSignature("well_researcher", "Research Well", "mind_lab", {"orientation": 0.85, "translation": 0.9}, {0: 0, 1: 1, 2: 2, 3: 3}),
        WellSignature("well_operator", "Operator Well", "mind_lab", {"contribution": 0.9, "journeyman_edge": 0.9}, {0: 0, 1: 1, 2: 1, 3: 2}),
    ]


def actor_zone_profile(actor: Actor) -> dict[str, float]:
    totals: dict[str, float] = {}
    weights: dict[str, float] = {}
    for e in actor.energy_history:
        w = max(e.energy_spend, 0.01)
        totals[e.zone] = totals.get(e.zone, 0.0) + e.grain_alignment * w
        weights[e.zone] = weights.get(e.zone, 0.0) + w
    return {z: totals[z] / weights[z] for z in totals if weights[z]}


def rank_destinations(actor: Actor, origin_surface: SurfaceTexture, wells: list[WellSignature]) -> list[RoutingCandidate]:
    profile = actor_zone_profile(actor)
    candidates: list[RoutingCandidate] = []
    for well in wells:
        overlap = set(profile) & set(well.zone_affinities)
        if not overlap:
            score = 0.0
        else:
            score = sum((1.0 - abs(profile[z] - well.zone_affinities[z])) for z in overlap) / len(overlap)
        candidates.append(RoutingCandidate(
            well_id=well.well_id,
            name=well.name,
            score=round(max(0.0, min(1.0, score)), 4),
            reason=f"matched {len(overlap)} surface zones against {well.name}",
            translated_altitude=well.altitude_translation.get(actor.sigma.altitude, 0),
        ))
    return sorted(candidates, key=lambda c: c.score, reverse=True)
