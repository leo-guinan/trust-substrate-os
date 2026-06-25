"""Synthetic cohorts for UI/test snapshots."""
from __future__ import annotations

from datetime import datetime, timedelta

from .engine import ScoringEngine
from .graduation import graduate_to_journeyman
from .models import EnergyEvent, Outcome, ReceiptStatus, RoutingKind, Tier
from .receipts import make_receipt, settle_receipt
from .surfaces import mind_lab_surface


def _event(now: datetime, days: int, zone: str, route: str, grain: float, energy: float = 2.0, dest: str | None = None) -> EnergyEvent:
    meta = {"destination": dest} if dest else {}
    return EnergyEvent(now - timedelta(days=days), energy, zone, route, grain, Outcome.COMPLETED, meta)


def fake_apprentice_cohort(n: int = 42) -> ScoringEngine:
    surface = mind_lab_surface()
    engine = ScoringEngine(surface)
    now = datetime.utcnow()
    archetypes = ["ready", "active", "blocked", "route", "synth", "turn", "decayed", "needs"]
    for i in range(n):
        kind = archetypes[i % len(archetypes)]
        cred = f"cred_{i:03d}"
        actor = engine.register_actor(cred)
        if kind == "needs":
            engine.record_impression(cred, _event(now, 0, "orientation", "reads_foundation", 0.6, 0.2))
            continue
        actor.tier = Tier.APPRENTICE
        for j, zone in enumerate(["orientation", "translation", "application"]):
            grain = 0.82 if kind in {"ready", "blocked", "active", "decayed"} else 0.32 if kind in {"route", "synth"} else 0.85
            days = 40 if kind == "decayed" else max(0, 8 - j)
            engine.record_impression(cred, _event(now, days, zone, "specific_case_analysis", grain, 2.0))
        if kind in {"ready", "blocked"}:
            for k in range(3):
                r = make_receipt(cred, RoutingKind.EXISTING_WELL, "mind_lab", "fixture receipt", 0.7, now - timedelta(days=7-k), settle_after_events=1)
                engine.receipts.append(settle_receipt(r, [_event(now, 0, "mind_lab", "settle", 0.8, 1.5)]))
            engine.sigma_engine.update_actor_sigma(actor, engine.receipts)
            if kind == "blocked":
                # kept as ready; capacity policy in flow tests/UI can mark blocked by cap
                pass
        elif kind == "route":
            engine.issue_receipt(cred, RoutingKind.EXISTING_WELL, "well_researcher", "better fit at researcher well", 0.7)
        elif kind == "synth":
            engine.issue_receipt(cred, RoutingKind.SYNTHETIC_WELL, "synthetic_application_well", "no current fit; synthesize destination", 0.45)
        elif kind == "turn":
            actor.is_trusted = True
            engine.record_impression(cred, _event(now, 0, "contribution", "asks_for_access", 0.1, 3.0))
            engine.flag_turn_review(cred, "recent contribution path diverged")
        engine.sigma_engine.update_actor_sigma(actor, engine.receipts)
    return engine
