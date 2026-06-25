"""Core scoring/impression engine.

Maps observed behavior → orbital radius and geodesic.
This is the foundation the rest of the system rests on.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Sequence

from .gates import evaluate_gate_0, evaluate_gate_1, evaluate_gate_2
from .models import (
    ENERGY_SCALE,
    ORBIT_MAX,
    ORBIT_MIN,
    Actor,
    EnergyEvent,
    Gate,
    GateResult,
    OrbitSummary,
    SurfaceTexture,
)


class ScoringEngine:
    """Stateful per-actor scoring within one operator's well."""

    def __init__(self, surface: SurfaceTexture):
        if not surface.zones:
            raise ValueError("Surface must define at least one zone")
        self.surface = surface
        self.actors: dict[str, Actor] = {}
        self.history: list[tuple[datetime, str, str, float]] = []  # ts, cred, zone, energy

    def register_actor(self, credential: str) -> Actor:
        if credential in self.actors:
            return self.actors[credential]
        actor = Actor(credential=credential)
        self.actors[credential] = actor
        return actor

    def record_impression(
        self,
        credential: str,
        event: EnergyEvent,
    ) -> Actor:
        """Record an energy event and update the actor's state."""
        actor = self.register_actor(credential)
        actor.energy_history.append(event)
        actor.last_active = event.timestamp
        self.history.append((event.timestamp, credential, event.zone, event.energy_spend))
        self._recalculate_orbit(actor)
        return actor

    def batch_record(self, impressions: list[tuple[str, EnergyEvent]]) -> list[Actor]:
        """Record multiple impressions efficiently."""
        updated = []
        for cred, ev in impressions:
            updated.append(self.record_impression(cred, ev))
        return updated

    def evaluate_membrane(self, credential: str) -> list[GateResult]:
        """Run all three membrane gates for an actor. Returns ordered results."""
        actor = self.actors.get(credential)
        if actor is None:
            actor = self.register_actor(credential)

        results: list[GateResult] = []
        
        # Gate 0
        r0 = evaluate_gate_0(actor, self.surface)
        results.append(r0)
        actor.gate_passes.append((Gate.DETECTION, r0.passed, r0.confidence))
        
        # Gate 1
        if r0.passed:
            r1 = evaluate_gate_1(actor, self.surface)
            results.append(r1)
            actor.gate_passes.append((Gate.FRIEND_FOE, r1.passed, r1.confidence))
            
            # Gate 2
            if r1.passed:
                r2 = evaluate_gate_2(actor, self.surface)
                results.append(r2)
                actor.gate_passes.append((Gate.FIT_MISFIT, r2.passed, r2.confidence))
                
                if r2.passed:
                    actor.is_trusted = True
                elif r2.routed_to and r2.routed_to.startswith("_"):
                    pass  # insufficient data or open network fallback
                # misfits are not ejected; they're routed

        return results

    def eject(self, credential: str, reason: str = "") -> Actor | None:
        """Eject an actor from the trusted zone."""
        actor = self.actors.get(credential)
        if actor is None or actor.is_ejected:
            return None
        actor.is_ejected = True
        actor.is_trusted = False
        actor.ejected_at = datetime.utcnow()
        # Ejection is a strong negative signal
        actor.current_orbit = min(1.0, actor.current_orbit + 0.5)
        return actor

    def geodesic_read(self, credential: str) -> OrbitSummary:
        """Produce the per-actor path-vs-grain read (Section 6)."""
        actor = self.actors.get(credential)
        if actor is None:
            raise KeyError(f"Actor {credential} not registered")

        # Gate progress string
        gate_map = {
            Gate.DETECTION: "G0",
            Gate.FRIEND_FOE: "G1",
            Gate.FIT_MISFIT: "G2",
        }
        gate_progress = [
            f"{gate_map[g]}{'✓' if p else '✗'}"
            for g, p, _ in actor.gate_passes
        ]

        # Recent deformation (last 24h of energy)
        cutoff = datetime.utcnow() - timedelta(hours=24)
        recent = [e for e in actor.energy_history if e.timestamp >= cutoff]
        recent_deformation = sum(e.energy_spend for e in recent)

        # With-grain percentage
        if recent:
            with_grain = sum(1 for e in recent if e.grain_alignment >= 0.5) / len(recent)
        else:
            with_grain = 0.0

        # Efficiency: did they take low-energy routes to outcomes?
        completed = [e for e in actor.energy_history if e.outcome.value == "completed"]
        if completed:
            efficiency = sum(e.energy_spend for e in completed) / max(len(completed), 1)
            efficiency = max(0.0, 1.0 - efficiency / 5.0)  # normalize, cap at 1.0
        else:
            efficiency = 0.0

        # Divergence: how often did they route against grain toward extraction-like outcomes?
        against_grain = [e for e in actor.energy_history if e.grain_alignment < 0.3]
        divergence = min(1.0, len(against_grain) / max(len(actor.energy_history), 1) * 2)

        # Trend
        if len(recent) >= 2:
            first_half = recent[: len(recent) // 2]
            second_half = recent[len(recent) // 2 :]
            first_energy = sum(e.energy_spend for e in first_half)
            second_energy = sum(e.energy_spend for e in second_half)
            if second_energy > first_energy * 1.2:
                trend = "rising"
            elif second_energy < first_energy * 0.8:
                trend = "decaying"
            else:
                trend = "steady"
        else:
            trend = "steady"

        return OrbitSummary(
            credential=actor.credential,
            orbit=actor.current_orbit,
            gate_progress=gate_progress,
            recent_deformation=recent_deformation,
            with_grain_pct=with_grain,
            efficiency=efficiency,
            divergence=divergence,
            energy_trend=trend,
        )

    def _recalculate_orbit(self, actor: Actor) -> None:
        """Decaying orbit based on recent net energy toward the well."""
        if not actor.energy_history:
            actor.current_orbit = ORBIT_MAX
            return

        # Weighted sum of energy events with exponential decay
        now = datetime.utcnow()
        half_life = timedelta(hours=self.surface.decay_half_life_hours)
        decay_constant = 0.693147 / half_life.total_seconds()  # ln(2)/half-life
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        for event in actor.energy_history:
            age = (now - event.timestamp).total_seconds()
            weight = 2.71828 ** (-decay_constant * age)  # e^(-λt)
            # Grain-aligned energy counts more; against-grain counts less
            effective_energy = event.energy_spend * (0.5 + 0.5 * event.grain_alignment)
            weighted_sum += effective_energy * weight
            total_weight += weight
        
        if total_weight == 0:
            actor.current_orbit = ORBIT_MAX
            return
        
        # Map to orbit: more energy → closer orbit
        net_energy = weighted_sum / total_weight
        # Energy of ~5 gets you to surface (orbit=0)
        orbit = max(ORBIT_MIN, min(ORBIT_MAX, 1.0 - net_energy / 5.0))
        actor.current_orbit = orbit

    def flow_health(self) -> dict:
        """Capacity-bounded flow metrics."""
        total = len(self.actors)
        trusted = sum(1 for a in self.actors.values() if a.is_trusted)
        ejected = sum(1 for a in self.actors.values() if a.is_ejected)
        
        # Gate throughput
        g0_pass = sum(1 for a in self.actors.values() if any(p for g, p, _ in a.gate_passes if g == Gate.DETECTION))
        g1_pass = sum(1 for a in self.actors.values() if any(p for g, p, _ in a.gate_passes if g == Gate.FRIEND_FOE and p))
        g2_pass = trusted
        
        return {
            "total": total,
            "trusted": trusted,
            "ejected": ejected,
            "pending": total - trusted - ejected,
            "gate_0_pass_rate": g0_pass / max(total, 1),
            "gate_1_pass_rate": g1_pass / max(g0_pass, 1),
            "gate_2_pass_rate": g2_pass / max(g1_pass, 1),
            "overall_conversion": g2_pass / max(total, 1),
        }
