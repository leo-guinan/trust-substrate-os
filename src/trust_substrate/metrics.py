"""Metric functions for the honest dashboard."""
from __future__ import annotations

from .models import Actor, PredictionReceipt, ReceiptStatus, RoutingKind, Tier


def receipt_settlement_rate(receipts: list[PredictionReceipt]) -> float:
    if not receipts:
        return 0.0
    settled = sum(1 for r in receipts if r.status in {ReceiptStatus.CONFIRMED, ReceiptStatus.DISCONFIRMED})
    return settled / len(receipts)


def false_capture_rate(actors: list[Actor]) -> float:
    trusted = [a for a in actors if a.is_trusted or a.tier in {Tier.APPRENTICE, Tier.JOURNEYMAN}]
    if not trusted:
        return 0.0
    false_captures = sum(1 for a in trusted if a.sigma.sigma_w > 0.7 or a.is_ejected)
    return false_captures / len(trusted)


def membrane_integrity(actors: list[Actor]) -> float:
    return max(0.0, 1.0 - false_capture_rate(actors))


def signal_to_noise_inner_orbit(actors: list[Actor], threshold: float = 0.4) -> float:
    inner = [a for a in actors if a.current_orbit <= threshold]
    if not inner:
        return 0.0
    good = sum(1 for a in inner if a.sigma.sigma_w <= 0.35)
    return good / len(inner)


def synthetic_fit_success_rate(receipts: list[PredictionReceipt]) -> float:
    synth = [r for r in receipts if r.kind == RoutingKind.SYNTHETIC_WELL]
    if not synth:
        return 0.0
    return sum(1 for r in synth if r.status == ReceiptStatus.CONFIRMED) / len(synth)


def rejection_latency(receipts: list[PredictionReceipt]) -> float:
    routed = [r for r in receipts if r.kind in {RoutingKind.EXISTING_WELL, RoutingKind.SYNTHETIC_WELL}]
    if not routed:
        return 0.0
    # Placeholder until gate index is added to receipts: earlier issued receipts are treated as lower latency.
    return 1.0 / max(1, len(routed))


def dashboard_metrics(actors: list[Actor], receipts: list[PredictionReceipt]) -> dict:
    return {
        "receipt_settlement_rate": receipt_settlement_rate(receipts),
        "false_capture_rate": false_capture_rate(actors),
        "membrane_integrity": membrane_integrity(actors),
        "signal_to_noise_inner_orbit": signal_to_noise_inner_orbit(actors),
        "synthetic_fit_success_rate": synthetic_fit_success_rate(receipts),
        "rejection_latency_proxy": rejection_latency(receipts),
    }
