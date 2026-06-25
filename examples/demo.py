#!/usr/bin/env python3
"""Quick demo of the Trust Substrate OS scoring engine.

Run: PYTHONPATH=src python examples/demo.py
"""
from datetime import datetime, timedelta

from trust_substrate import (
    ScoringEngine,
    SurfaceTexture,
    ZoneGrain,
    EnergyEvent,
    Outcome,
    Gate,
)


def main():
    surface = SurfaceTexture(
        well_id="lens_well",
        zones={
            "landing": ZoneGrain(
                zone_id="landing",
                typical_routes={
                    "home": 0.8,
                    "blog": 0.6,
                    "random": 0.2,
                },
                energy_cost_mean=0.3,
                energy_cost_std=0.1,
            ),
            "depth": ZoneGrain(
                zone_id="depth",
                typical_routes={
                    "lens_read": 0.95,
                    "chat": 0.85,
                    "export": 0.1,
                },
                energy_cost_mean=2.5,
                energy_cost_std=0.8,
            ),
        },
        decay_half_life_hours=72.0,
    )

    engine = ScoringEngine(surface)

    # Actor A: genuine fit
    fit = "fit_demo"
    now = datetime.utcnow()
    engine.record_impression(fit, EnergyEvent(timestamp=now, energy_spend=0.2, zone="landing", route_taken="home", grain_alignment=0.8))
    for r, g in [("lens_read", 0.95), ("chat", 0.9), ("lens_read", 0.95)]:
        engine.record_impression(fit, EnergyEvent(timestamp=now + timedelta(minutes=2), energy_spend=2.0, zone="depth", route_taken=r, grain_alignment=g))
    res_fit = engine.evaluate_membrane(fit)
    summary_fit = engine.geodesic_read(fit)

    # Actor B: extractive bent
    ext = "ext_demo"
    engine.record_impression(ext, EnergyEvent(timestamp=now, energy_spend=0.1, zone="landing", route_taken="random", grain_alignment=0.2))
    for r, g in [("export", 0.1), ("export", 0.1), ("random", 0.2)]:
        engine.record_impression(ext, EnergyEvent(timestamp=now + timedelta(minutes=1), energy_spend=1.5, zone="depth", route_taken=r, grain_alignment=g))
    res_ext = engine.evaluate_membrane(ext)
    summary_ext = engine.geodesic_read(ext)

    print("=== Fit actor ===")
    print(f"  Gates: {[f'{r.gate.name}: passed={r.passed}, confidence={r.confidence:.2f}' for r in res_fit]}")
    print(f"  Orbit: {summary_fit.orbit:.3f}")
    print(f"  With-grain: {summary_fit.with_grain_pct:.1%}")
    print(f"  Trusted: {engine.actors[fit].is_trusted}")

    print("\n=== Extractive actor ==")
    gate_strs = []
    for r in res_ext:
        dest = r.routed_to if r.routed_to else "continue"
        gate_strs.append(f"{r.gate.name}: passed={r.passed} -> {dest}")
    print(f"  Gates: {gate_strs}")
    print(f"  Orbit: {summary_ext.orbit:.3f}")
    print(f"  With-grain: {summary_ext.with_grain_pct:.1%}")
    if res_ext and res_ext[-1].routed_to:
        print(f"  Routed to wormhole: {res_ext[-1].routed_to}")

    print("\n=== Flow health ===")
    print(engine.flow_health())


if __name__ == "__main__":
    main()
