#!/usr/bin/env python3
"""Export a fake/live-ish apprentice flow snapshot for static UI."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path

from trust_substrate.capacity import seat_snapshot
from trust_substrate.fakes import fake_apprentice_cohort
from trust_substrate.flow import build_flow_queue
from trust_substrate.metrics import dashboard_metrics
from trust_substrate.models import ReceiptStatus, RoutingKind, SeatPolicy
from trust_substrate.predictions import prediction_registry
from trust_substrate.sun import scan_repo


def encode(obj):
    if is_dataclass(obj):
        return {k: encode(v) for k, v in asdict(obj).items()}
    if isinstance(obj, list):
        return [encode(x) for x in obj]
    if isinstance(obj, dict):
        return {k: encode(v) for k, v in obj.items()}
    if hasattr(obj, "value"):
        return obj.value
    return obj


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="docs/flow.json")
    parser.add_argument("--sun-repo", default="/Users/leoguinan/Projects/mind-lab")
    parser.add_argument("--n", type=int, default=48)
    args = parser.parse_args()

    engine = fake_apprentice_cohort(args.n)
    policy = SeatPolicy(journeyman_cap=6)  # intentionally tight to show blocked state
    actors = list(engine.actors.values())
    queue = build_flow_queue(actors, engine.receipts, policy)
    sun = scan_repo(args.sun_repo)
    capacity = seat_snapshot(actors, policy)
    metrics = dashboard_metrics(actors, engine.receipts)
    lambda_rate = sum(a.sigma.lambda_rate for a in actors) / max(len(actors), 1)

    payload = {
        "sun": encode(sun),
        "capacity": encode(capacity),
        "lambda": {"rate": round(lambda_rate, 3), "window_days": 14, "principle": "trust grows no faster than settled receipts"},
        "metrics": metrics,
        "actors": [
            {
                "credential": a.credential,
                "tier": a.tier.value,
                "orbit": round(a.current_orbit, 3),
                "sigma_w": a.sigma.sigma_w,
                "sigma_s": a.sigma.sigma_s,
                "lambda_rate": a.sigma.lambda_rate,
                "altitude": a.sigma.altitude,
                "events": len(a.energy_history),
                "last_active": a.last_active.isoformat(),
            }
            for a in actors
        ],
        "queue": [
            {
                "credential": item.credential,
                "decision": item.decision.value,
                "priority": item.priority,
                "reason": item.reason,
                "recommended_action": item.recommended_action,
                "receipt_id": item.receipt_id,
            }
            for item in queue
        ],
        "receipts": [
            {
                "receipt_id": r.receipt_id,
                "credential": r.credential,
                "kind": r.kind.value,
                "destination": r.predicted_destination,
                "confidence": r.confidence,
                "status": r.status.value,
                "prediction": r.prediction,
                "settlement_reason": r.settlement_reason,
            }
            for r in engine.receipts
        ],
        "predictions": [encode(p) for p in prediction_registry()],
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    json_text = json.dumps(payload, indent=2)
    out.write_text(json_text)
    js_out = out.with_name(out.stem + "-data.js")
    js_out.write_text("window.FLOW_DATA = " + json_text + ";\n")
    print(f"wrote {out} and {js_out} with {len(actors)} actors, {len(engine.receipts)} receipts, {len(queue)} queue items")


if __name__ == "__main__":
    main()
