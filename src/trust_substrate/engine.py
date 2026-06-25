"""Core scoring/impression engine.

Maps observed behavior → orbital radius, geodesic, σ state, and receipt-backed flow.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from .gates import evaluate_gate_0, evaluate_gate_1, evaluate_gate_2
from .models import (
    ORBIT_MAX,
    ORBIT_MIN,
    Actor,
    EnergyEvent,
    Gate,
    GateResult,
    OrbitSummary,
    PredictionReceipt,
    RoutingKind,
    SurfaceTexture,
    Tier,
)
from .receipts import make_receipt, settle_receipt
from .sigma import SigmaEngine


class ScoringEngine:
    """Stateful per-actor scoring within one operator's well."""

    def __init__(self, surface: SurfaceTexture):
        if not surface.zones:
            raise ValueError("Surface must define at least one zone")
        self.surface = surface
        self.actors: dict[str, Actor] = {}
        self.history: list[tuple[datetime, str, str, float]] = []  # ts, cred, zone, energy
        self.receipts: list[PredictionReceipt] = []
        self.sigma_engine = SigmaEngine()

    def register_actor(self, credential: str) -> Actor:
        if credential in self.actors:
            return self.actors[credential]
        actor = Actor(credential=credential)
        self.actors[credential] = actor
        return actor

    def record_impression(self, credential: str, event: EnergyEvent) -> Actor:
        """Record a posted event and update orbit + σ."""
        actor = self.register_actor(credential)
        actor.energy_history.append(event)
        actor.last_active = event.timestamp
        self.history.append((event.timestamp, credential, event.zone, event.energy_spend))
        self._recalculate_orbit(actor)
        self.settle_receipts(credential)
        self.sigma_engine.update_actor_sigma(actor, self.receipts)
        return actor

    def batch_record(self, impressions: list[tuple[str, EnergyEvent]]) -> list[Actor]:
        return [self.record_impression(cred, ev) for cred, ev in impressions]

    def issue_receipt(
        self,
        credential: str,
        kind: RoutingKind,
        predicted_destination: str,
        prediction: str,
        confidence: float,
        settle_after_events: int = 3,
    ) -> PredictionReceipt:
        receipt = make_receipt(
            credential=credential,
            kind=kind,
            predicted_destination=predicted_destination,
            prediction=prediction,
            confidence=confidence,
            settle_after_events=settle_after_events,
        )
        self.receipts.append(receipt)
        actor = self.register_actor(credential)
        self.sigma_engine.update_actor_sigma(actor, self.receipts)
        return receipt

    def settle_receipts(self, credential: str) -> list[PredictionReceipt]:
        actor = self.actors.get(credential)
        if actor is None:
            return []
        updated: list[PredictionReceipt] = []
        for receipt in self.receipts:
            if receipt.credential != credential:
                updated.append(receipt)
                continue
            updated.append(settle_receipt(receipt, actor.energy_history))
        self.receipts = updated
        return [r for r in self.receipts if r.credential == credential]

    def evaluate_membrane(self, credential: str) -> list[GateResult]:
        """Run all three membrane gates for an actor. Misfits route with receipts."""
        actor = self.actors.get(credential) or self.register_actor(credential)
        results: list[GateResult] = []

        r0 = evaluate_gate_0(actor, self.surface)
        results.append(r0)
        actor.gate_passes.append((Gate.DETECTION, r0.passed, r0.confidence))

        if r0.passed:
            r1 = evaluate_gate_1(actor, self.surface)
            results.append(r1)
            actor.gate_passes.append((Gate.FRIEND_FOE, r1.passed, r1.confidence))

            if r1.passed:
                r2 = evaluate_gate_2(actor, self.surface)
                results.append(r2)
                actor.gate_passes.append((Gate.FIT_MISFIT, r2.passed, r2.confidence))

                if r2.passed:
                    actor.is_trusted = True
                    if actor.tier == Tier.VISITOR:
                        actor.tier = Tier.APPRENTICE
                elif r2.routed_to and not r2.routed_to.startswith("_"):
                    receipt = self.issue_receipt(
                        credential,
                        RoutingKind.EXISTING_WELL,
                        r2.routed_to,
                        f"This credential will settle better at {r2.routed_to} than at {self.surface.well_id}.",
                        r2.confidence,
                    )
                    r2.receipt_id = receipt.receipt_id
        self.sigma_engine.update_actor_sigma(actor, self.receipts)
        return results

    def flag_turn_review(self, credential: str, reason: str = "rising σ_w") -> PredictionReceipt:
        """Issue a losable revocation-review receipt. Does not trap or terminally eject."""
        actor = self.register_actor(credential)
        return self.issue_receipt(
            credential,
            RoutingKind.REVOCATION_REVIEW,
            "revocation_review",
            f"This trusted member may have turned extractive: {reason}. Subsequent events can confirm or disconfirm.",
            min(1.0, max(0.5, actor.sigma.sigma_w)),
        )

    def eject(self, credential: str, reason: str = "manual override") -> Actor | None:
        """Manual terminal override. Automated flow should use flag_turn_review()."""
        actor = self.actors.get(credential)
        if actor is None or actor.is_ejected:
            return None
        actor.is_ejected = True
        actor.is_trusted = False
        actor.ejected_at = datetime.utcnow()
        actor.current_orbit = min(1.0, actor.current_orbit + 0.5)
        self.issue_receipt(
            credential,
            RoutingKind.REVOCATION_REVIEW,
            "manual_ejection",
            f"Manual ejection should be confirmed by subsequent lack of with-grain events: {reason}.",
            0.8,
        )
        return actor

    def geodesic_read(self, credential: str) -> OrbitSummary:
        """Produce the per-actor path-vs-grain read."""
        actor = self.actors.get(credential)
        if actor is None:
            raise KeyError(f"Actor {credential} not registered")

        gate_map = {Gate.DETECTION: "G0", Gate.FRIEND_FOE: "G1", Gate.FIT_MISFIT: "G2"}
        gate_progress = [f"{gate_map[g]}{'✓' if p else '✗'}" for g, p, _ in actor.gate_passes]

        cutoff = datetime.utcnow() - timedelta(hours=24)
        recent = [e for e in actor.energy_history if e.timestamp >= cutoff]
        recent_deformation = sum(e.energy_spend for e in recent)
        with_grain = sum(1 for e in recent if e.grain_alignment >= 0.5) / len(recent) if recent else 0.0

        completed = [e for e in actor.energy_history if e.outcome and e.outcome.value == "completed"]
        if completed:
            efficiency = sum(e.energy_spend for e in completed) / max(len(completed), 1)
            efficiency = max(0.0, 1.0 - efficiency / 5.0)
        else:
            efficiency = 0.0

        against_grain = [e for e in actor.energy_history if e.grain_alignment < 0.3]
        divergence = min(1.0, len(against_grain) / max(len(actor.energy_history), 1) * 2)

        if len(recent) >= 2:
            first_half = recent[: len(recent) // 2]
            second_half = recent[len(recent) // 2 :]
            first_energy = sum(e.energy_spend for e in first_half)
            second_energy = sum(e.energy_spend for e in second_half)
            trend = "rising" if second_energy > first_energy * 1.2 else "decaying" if second_energy < first_energy * 0.8 else "steady"
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
            sigma_w=actor.sigma.sigma_w,
            sigma_s=actor.sigma.sigma_s,
            lambda_rate=actor.sigma.lambda_rate,
            altitude=actor.sigma.altitude,
        )

    def _recalculate_orbit(self, actor: Actor) -> None:
        """Decaying orbit based on recent net energy toward the well."""
        if not actor.energy_history:
            actor.current_orbit = ORBIT_MAX
            return
        now = datetime.utcnow()
        half_life = timedelta(hours=self.surface.decay_half_life_hours)
        decay_constant = 0.693147 / half_life.total_seconds()
        weighted_sum = 0.0
        total_weight = 0.0
        for event in actor.energy_history:
            age = (now - event.timestamp).total_seconds()
            weight = 2.71828 ** (-decay_constant * age)
            effective_energy = event.energy_spend * (0.5 + 0.5 * event.grain_alignment)
            weighted_sum += effective_energy * weight
            total_weight += weight
        if total_weight == 0:
            actor.current_orbit = ORBIT_MAX
            return
        net_energy = weighted_sum / total_weight
        actor.current_orbit = max(ORBIT_MIN, min(ORBIT_MAX, 1.0 - net_energy / 5.0))

    def flow_health(self) -> dict:
        """Capacity-bounded flow metrics."""
        total = len(self.actors)
        trusted = sum(1 for a in self.actors.values() if a.is_trusted)
        ejected = sum(1 for a in self.actors.values() if a.is_ejected)
        g0_pass = sum(1 for a in self.actors.values() if any(p for g, p, _ in a.gate_passes if g == Gate.DETECTION))
        g1_pass = sum(1 for a in self.actors.values() if any(p for g, p, _ in a.gate_passes if g == Gate.FRIEND_FOE and p))
        g2_pass = trusted
        return {
            "total": total,
            "trusted": trusted,
            "ejected": ejected,
            "pending": total - trusted - ejected,
            "apprentices": sum(1 for a in self.actors.values() if a.tier == Tier.APPRENTICE),
            "journeymen": sum(1 for a in self.actors.values() if a.tier == Tier.JOURNEYMAN),
            "gate_0_pass_rate": g0_pass / max(total, 1),
            "gate_1_pass_rate": g1_pass / max(g0_pass, 1),
            "gate_2_pass_rate": g2_pass / max(g1_pass, 1),
            "overall_conversion": g2_pass / max(total, 1),
        }
