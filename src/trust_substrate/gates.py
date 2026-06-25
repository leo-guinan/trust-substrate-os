"""Membrane gate implementations."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from .models import Actor, EnergyEvent, Gate, GateResult, Outcome, SurfaceTexture

if TYPE_CHECKING:
    pass


def evaluate_gate_0(actor: Actor, surface: SurfaceTexture) -> GateResult:
    """Gate 0 — Detection: intent, or drift?
    
    Reads volume & pattern. Asks for nothing yet.
    Rejects bots, scrapers, noise, accidental traffic.
    Cost to operator: ~0.
    """
    if actor.is_ejected:
        return GateResult(
            gate=Gate.DETECTION,
            passed=False,
            confidence=1.0,
            reasoning="Actor previously ejected",
        )
    
    # Too few events to judge = pass (innocent until proven noisy)
    if len(actor.energy_history) < 2:
        return GateResult(
            gate=Gate.DETECTION,
            passed=True,
            confidence=0.5,
            reasoning="Insufficient signal; passing to Gate 1",
        )
    
    # Pattern: burst then silence = likely bot/scraper
    events = actor.energy_history
    if len(events) >= 3:
        first_three = events[:3]
        spans = [
            (first_three[i+1].timestamp - first_three[i].timestamp).total_seconds()
            for i in range(len(first_three) - 1)
        ]
        avg_span = sum(spans) / len(spans) if spans else 9999
        
        if avg_span < 2.0:  # sub-2-second intervals
            return GateResult(
                gate=Gate.DETECTION,
                passed=False,
                confidence=0.85,
                reasoning="Burst pattern consistent with automated access",
            )
    
    # High-energy click-and-leave = accidental or harvesting
    recent = _recent_events(actor, timedelta(minutes=5))
    if len(recent) == 1 and recent[0].energy_spend < 0.1:
        return GateResult(
            gate=Gate.DETECTION,
            passed=False,
            confidence=0.6,
            reasoning="Single low-energy touch; likely accidental or shallow",
        )
    
    return GateResult(
        gate=Gate.DETECTION,
        passed=True,
        confidence=0.7,
        reasoning="Passed detection filter",
    )


def evaluate_gate_1(
    actor: Actor, surface: SurfaceTexture, interaction: EnergyEvent | None = None
) -> GateResult:
    """Gate 1 — Friend or foe: extractive?
    
    Reads response to a contextual costly signal.
    Rejects pitch-bots, harvesters, parallelized actors.
    Cost to operator: low.
    """
    if not actor.gate_passes or actor.gate_passes[-1][0] != Gate.DETECTION or not actor.gate_passes[-1][1]:
        return GateResult(
            gate=Gate.FRIEND_FOE,
            passed=False,
            confidence=0.0,
            reasoning="Must pass Gate 0 first",
        )
    
    # Needs at least one meaningful interaction with the costly surface
    meaningful = [e for e in actor.energy_history if e.energy_spend >= 1.0]
    if not meaningful:
        return GateResult(
            gate=Gate.FRIEND_FOE,
            passed=False,
            confidence=0.8,
            reasoning="No costly signal observed; extractive actors avoid energy spend",
        )
    
    # Check for parallelized behavior: same route, high speed, low depth
    routes = [e.route_taken for e in meaningful]
    unique_routes = set(routes)
    if len(meaningful) >= 3 and len(unique_routes) == 1:
        # Same route repeated, likely template/parallelized
        return GateResult(
            gate=Gate.FRIEND_FOE,
            passed=False,
            confidence=0.75,
            reasoning="Repeated identical route; template behavior",
        )
    
    # Genuine engagement shows grain-aligned diversity
    grain_scores = [e.grain_alignment for e in meaningful]
    avg_grain = sum(grain_scores) / len(grain_scores)
    
    if avg_grain < 0.2 and len(meaningful) >= 2:
        return GateResult(
            gate=Gate.FRIEND_FOE,
            passed=False,
            confidence=0.7,
            reasoning="Consistent against-grain routing; extraction bend",
        )
    
    return GateResult(
        gate=Gate.FRIEND_FOE,
        passed=True,
        confidence=0.65,
        reasoning="Grain-aligned costly engagement observed",
    )


def evaluate_gate_2(
    actor: Actor, surface: SurfaceTexture
) -> GateResult:
    """Gate 2 — Fit or misfit: this well's grain?
    
    Reads which way energy bends on a textured choice.
    Routes misfits to wormhole (re-home, not reject).
    Cost to operator: higher.
    """
    if not actor.gate_passes or actor.gate_passes[-1][0] != Gate.FRIEND_FOE or not actor.gate_passes[-1][1]:
        return GateResult(
            gate=Gate.FIT_MISFIT,
            passed=False,
            confidence=0.0,
            reasoning="Must pass Gate 1 first",
        )
    
    meaningful = [e for e in actor.energy_history if e.energy_spend >= 1.0]
    if len(meaningful) < 3:
        return GateResult(
            gate=Gate.FIT_MISFIT,
            passed=False,
            routed_to="_insufficient_data",
            confidence=0.5,
            reasoning="Not enough textured-surface data for fit read",
        )
    
    # Calculate grain alignment across zones
    grain_scores: dict[str, list[float]] = {}
    for e in meaningful:
        grain_scores.setdefault(e.zone, []).append(e.grain_alignment)
    
    zone_alignments = {
        zone: sum(scores) / len(scores) for zone, scores in grain_scores.items()
    }
    
    # Overall alignment
    all_scores = [s for scores in grain_scores.values() for s in scores]
    overall_alignment = sum(all_scores) / len(all_scores) if all_scores else 0.0
    
    # Fit = high alignment across the operator's primary zones
    primary_zones = _primary_zones(surface, actor)
    primary_scores = [zone_alignments.get(z, 0.0) for z in primary_zones]
    primary_avg = sum(primary_scores) / len(primary_scores) if primary_scores else 0.0
    
    if primary_avg >= 0.5:
        return GateResult(
            gate=Gate.FIT_MISFIT,
            passed=True,
            confidence=primary_avg,
            reasoning=f"Primary zone alignment {primary_avg:.2f}; good fit",
        )
    
    # Find best-fit well for wormhole routing
    best_target = _suggest_wormhole_target(actor, surface, zone_alignments)
    return GateResult(
        gate=Gate.FIT_MISFIT,
        passed=False,
        routed_to=best_target or "_open_network",
        confidence=1.0 - primary_avg,
        reasoning=f"Primary zone alignment {primary_avg:.2f}; misfit for this well",
    )


# --- Helpers ---

def _recent_events(actor: Actor, window: timedelta) -> list[EnergyEvent]:
    cutoff = datetime.utcnow() - window
    return [e for e in actor.energy_history if e.timestamp >= cutoff]


def _primary_zones(surface: SurfaceTexture, actor: Actor | None = None) -> list[str]:
    """Return the well's primary zone IDs, filtered to zones the actor actually touched meaningfully."""
    if actor is None:
        return list(surface.zones.keys())[:2]
    meaningful_zones = {e.zone for e in actor.energy_history if e.energy_spend >= 1.0}
    if not meaningful_zones:
        return list(surface.zones.keys())[:1]
    candidates = sorted(
        meaningful_zones,
        key=lambda z: surface.zones[z].energy_cost_mean,
        reverse=True,
    )
    return candidates[:2]


def _suggest_wormhole_target(
    actor: Actor, surface: SurfaceTexture, alignments: dict[str, float]
) -> str | None:
    """Placeholder: match zone alignment to known-well signatures."""
    # In a live system this queries the substrate network.
    # For now: return a deterministic placeholder based on credential hash.
    h = hash(actor.credential)
    candidates = ["well_alpha", "well_beta", "well_gamma"]
    return candidates[h % len(candidates)] if candidates else None
