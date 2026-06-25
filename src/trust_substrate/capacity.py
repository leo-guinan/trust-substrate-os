"""Capacity-bound seat mechanics."""
from __future__ import annotations

from .models import Actor, SeatPolicy, SeatSnapshot, Tier


def seat_snapshot(actors: list[Actor], policy: SeatPolicy) -> SeatSnapshot:
    apprentice_active = sum(1 for a in actors if a.tier == Tier.APPRENTICE and not a.is_ejected)
    journeyman_active = sum(1 for a in actors if a.tier == Tier.JOURNEYMAN and not a.is_ejected)
    return SeatSnapshot(
        apprentice_active=apprentice_active,
        journeyman_active=journeyman_active,
        apprentice_open=max(0, policy.apprentice_cap - apprentice_active),
        journeyman_open=max(0, policy.journeyman_cap - journeyman_active),
    )


def has_journeyman_capacity(snapshot: SeatSnapshot) -> bool:
    return snapshot.journeyman_open > 0
