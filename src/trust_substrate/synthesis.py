"""Provisional well synthesis from misfit deformations."""
from __future__ import annotations

import hashlib

from .models import Actor, PredictionReceipt, ProvisionalWellSpec


def synthesize_well(actor: Actor, receipt: PredictionReceipt, source_corpora: list[str]) -> ProvisionalWellSpec:
    totals: dict[str, float] = {}
    weights: dict[str, float] = {}
    for e in actor.energy_history:
        w = max(e.energy_spend, 0.01)
        totals[e.zone] = totals.get(e.zone, 0.0) + (1.0 - e.grain_alignment) * w
        weights[e.zone] = weights.get(e.zone, 0.0) + w
    needed = {z: round(totals[z] / weights[z], 3) for z in totals if weights[z]}
    fingerprint = hashlib.sha256((actor.credential + receipt.receipt_id).encode()).hexdigest()[:10]
    strongest = max(needed, key=needed.get) if needed else "unmapped"
    return ProvisionalWellSpec(
        spec_id="synthetic_" + fingerprint,
        source_credential=actor.credential,
        generated_from_receipt_id=receipt.receipt_id,
        title=f"Provisional {strongest.replace('_', ' ').title()} Well",
        needed_grain=needed,
        source_corpora=source_corpora,
        confidence=min(0.45, receipt.confidence * 0.5),
    )
