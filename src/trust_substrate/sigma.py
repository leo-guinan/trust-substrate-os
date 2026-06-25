"""σ and λ mechanics for posted-event trust gaps."""
from __future__ import annotations

from datetime import datetime, timedelta

from .models import Actor, Gate, PredictionReceipt, ReceiptStatus, SigmaState, Tier


class SigmaEngine:
    """Compute σ_w, σ_s, λ, and altitude from events and settled receipts."""

    def __init__(self, window_days: int = 14):
        self.window_days = window_days

    def update_actor_sigma(
        self,
        actor: Actor,
        receipts: list[PredictionReceipt],
        now: datetime | None = None,
    ) -> SigmaState:
        now = now or datetime.utcnow()
        cutoff = now - timedelta(days=self.window_days)
        recent = [e for e in actor.energy_history if e.timestamp >= cutoff]
        if recent:
            total_energy = sum(max(e.energy_spend, 0.01) for e in recent)
            sigma_w = sum((1.0 - e.grain_alignment) * max(e.energy_spend, 0.01) for e in recent) / total_energy
        else:
            sigma_w = min(1.0, actor.sigma.sigma_w + 0.05) if actor.energy_history else 0.0

        relevant = [r for r in receipts if r.credential == actor.credential]
        pending = [r for r in relevant if r.status == ReceiptStatus.PENDING]
        disconfirmed = [r for r in relevant if r.status == ReceiptStatus.DISCONFIRMED]
        confirmed = [r for r in relevant if r.status == ReceiptStatus.CONFIRMED]
        settled_recent = [r for r in relevant if r.settled_at and r.settled_at >= cutoff]

        # self-gap rises when the system is carrying unsettled or contradictory claims.
        sigma_s = min(1.0, (len(pending) * 0.12) + (len(disconfirmed) * 0.2) - (len(confirmed) * 0.04))
        sigma_s = max(0.0, sigma_s)

        # λ = settled receipts per week in the measurement window.
        weeks = max(self.window_days / 7.0, 0.1)
        lambda_rate = len(settled_recent) / weeks

        altitude = self._altitude(actor, confirmed, lambda_rate, sigma_w, sigma_s)
        actor.sigma = SigmaState(
            sigma_w=round(sigma_w, 4),
            sigma_s=round(sigma_s, 4),
            lambda_rate=round(lambda_rate, 4),
            altitude=altitude,
            last_settlement_at=max((r.settled_at for r in settled_recent if r.settled_at), default=actor.sigma.last_settlement_at),
        )
        return actor.sigma

    def _altitude(self, actor: Actor, confirmed: list[PredictionReceipt], lambda_rate: float, sigma_w: float, sigma_s: float) -> int:
        if actor.tier == Tier.JOURNEYMAN:
            return 4
        if actor.tier == Tier.APPRENTICE and lambda_rate >= 0.2 and sigma_w <= 0.35 and sigma_s <= 0.35 and len(confirmed) >= 3:
            return 3
        if actor.tier == Tier.APPRENTICE or actor.is_trusted:
            return 2
        if any(g == Gate.FRIEND_FOE and passed for g, passed, _ in actor.gate_passes):
            return 1
        return 0
