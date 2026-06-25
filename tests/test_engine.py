"""Smoke tests for the Trust Substrate OS scoring engine."""
import pytest
from datetime import datetime, timedelta

from trust_substrate import (
    Actor,
    EnergyEvent,
    GateResult,
    OrbitSummary,
    ScoringEngine,
    SurfaceTexture,
    ZoneGrain,
    Outcome,
)


@pytest.fixture
def engine():
    surface = SurfaceTexture(
        well_id="well_test",
        zones={
            "entry": ZoneGrain(zone_id="entry", typical_routes={"landing": 0.8}, energy_cost_mean=0.5, energy_cost_std=0.1),
            "depth": ZoneGrain(zone_id="depth", typical_routes={"lens_read": 0.9, "honeypot": 0.1}, energy_cost_mean=2.0, energy_cost_std=0.5),
        },
        decay_half_life_hours=24.0,
    )
    return ScoringEngine(surface)


def test_register_and_orbit(engine):
    actor = engine.register_actor("cred_001")
    assert actor.current_orbit == 1.0  # cold start
    assert actor.credential == "cred_001"


def test_record_impression_decays_orbit(engine):
    actor = engine.actors["cred_002"] = engine.register_actor("cred_002")
    ev = EnergyEvent(
        timestamp=datetime.utcnow(),
        energy_spend=3.0,
        zone="depth",
        route_taken="lens_read",
        grain_alignment=0.9,
        outcome=Outcome.COMPLETED,
    )
    engine.record_impression("cred_002", ev)
    # Energy 3.0 * grain 0.9 * (0.5+0.45) = 2.85 effective; orbit = 1 - 2.85/5 = 0.43
    assert actor.current_orbit < 0.5  # should be near surface
    summary = engine.geodesic_read("cred_002")
    assert summary.with_grain_pct > 0.8


def test_gate_0_rejects_burst(engine):
    cred = "burst_bot"
    now = datetime.utcnow()
    # Inject rapid-fire events
    for i in range(4):
        engine.record_impression(
            cred,
            EnergyEvent(
                timestamp=now + timedelta(seconds=i),
                energy_spend=0.1,
                zone="entry",
                route_taken="landing",
                grain_alignment=0.5,
            ),
        )
    results = engine.evaluate_membrane(cred)
    assert results[0].passed is False
    assert "burst" in results[0].reasoning.lower() or "automated" in results[0].reasoning.lower()


def test_gate_1_requires_costly_signal(engine):
    cred = "cheap_visitor"
    now = datetime.utcnow()
    # Pass Gate 0 with casual traffic
    engine.record_impression(
        cred,
        EnergyEvent(
            timestamp=now,
            energy_spend=0.05,
            zone="entry",
            route_taken="landing",
            grain_alignment=0.5,
        ),
    )
    r0 = engine.evaluate_membrane(cred)
    assert r0[0].passed is True  # Gate 0 passes
    
    # Gate 1 should fail: no costly signal
    r1 = engine.evaluate_membrane(cred)
    assert r1[1].passed is False
    assert "costly" in r1[1].reasoning.lower() or "extractive" in r1[1].reasoning.lower()


def test_full_pass_gate_2_fit(engine):
    cred = "genuine_fit"
    now = datetime.utcnow()
    # Gate 0: casual but not burst
    engine.record_impression(cred, EnergyEvent(timestamp=now, energy_spend=0.2, zone="entry", route_taken="landing", grain_alignment=0.7))
    
    # Gate 1: costly, grain-aligned, varied primary-zone routes
    for route in ["lens_read", "depth_chat", "follow_up"]:
        engine.record_impression(cred, EnergyEvent(timestamp=now + timedelta(minutes=1), energy_spend=2.0, zone="depth", route_taken=route, grain_alignment=0.9))
    # also have meaningful entry events so Gate 2 can see alignment there too
    for route in ["landing", "cta_click"]:
        engine.record_impression(cred, EnergyEvent(timestamp=now + timedelta(minutes=1), energy_spend=1.5, zone="entry", route_taken=route, grain_alignment=0.8))
    
    results = engine.evaluate_membrane(cred)
    assert len(results) == 3
    assert results[1].passed is True
    assert results[2].passed is True
    assert engine.actors[cred].is_trusted is True


def test_gate_2_misfit_routes(engine):
    cred = "misfit_visitor"
    now = datetime.utcnow()
    # Pass Gate 0
    engine.record_impression(cred, EnergyEvent(timestamp=now, energy_spend=0.2, zone="entry", route_taken="landing", grain_alignment=0.6))
    
    # Gate 1 should still pass if against-grain is below threshold, to reach Gate 2
    # Use mix with some grain-aligned cost so Gate 1 avg_grain stays near 0.2+
    for route, grain in [("honeypot", 0.15), ("sidebar_click", 0.25), ("honeypot", 0.15), ("export_attempt", 0.25)]:
        engine.record_impression(cred, EnergyEvent(timestamp=now + timedelta(minutes=1), energy_spend=1.5, zone="depth", route_taken=route, grain_alignment=grain))
    engine.record_impression(cred, EnergyEvent(timestamp=now + timedelta(minutes=2), energy_spend=1.0, zone="entry", route_taken="cta", grain_alignment=0.2))
    
    results = engine.evaluate_membrane(cred)
    assert len(results) == 3
    assert results[1].passed is True
    assert results[2].passed is False
    assert results[2].routed_to is not None


def test_eject(engine):
    actor = engine.register_actor("bad_actor")
    engine.eject("bad_actor")
    assert actor.is_ejected is True
    assert actor.current_orbit >= 0.5  # moved far out
    r0 = engine.evaluate_membrane("bad_actor")
    assert r0[0].passed is False


def test_flow_health(engine):
    # Seed a few actors
    for i in range(10):
        cred = f"user_{i}"
        now = datetime.utcnow() - timedelta(minutes=i)
        engine.record_impression(
            cred,
            EnergyEvent(
                timestamp=now,
                energy_spend=1.0 if i < 4 else 0.1,
                zone="entry",
                route_taken="landing",
                grain_alignment=0.8 if i < 4 else 0.3,
            ),
        )
        if i < 4:
            # Give fits enough signal
            for _ in range(2):
                engine.record_impression(
                    cred,
                    EnergyEvent(
                        timestamp=now + timedelta(seconds=30),
                        energy_spend=2.0,
                        zone="depth",
                        route_taken="lens_read",
                        grain_alignment=0.9,
                    ),
                )
            engine.evaluate_membrane(cred)
    
    health = engine.flow_health()
    assert "total" in health
    assert health["total"] == 10
    assert health["overall_conversion"] >= 0.0
    assert health["overall_conversion"] <= 1.0
