#!/usr/bin/env python3
"""Export satellite factory snapshot for static UI."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path

from trust_substrate.satellite_fakes import fake_satellite_factory


def encode(obj):
    if is_dataclass(obj) and not isinstance(obj, type):
        return {k: encode(v) for k, v in asdict(obj).items()}
    if isinstance(obj, list):
        return [encode(x) for x in obj]
    if isinstance(obj, dict):
        return {k: encode(v) for k, v in obj.items()}
    if hasattr(obj, "value"):
        return obj.value
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return obj


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="docs/satellites.json")
    args = parser.parse_args()
    factory = fake_satellite_factory()
    deployments = list(factory.deployments.values())
    credentials = sorted({r.credential for d in deployments for r in d.reactions})
    reads = [factory.triangulate(c) for c in credentials]
    payload = {
        "well_id": factory.well_id,
        "principle": "Satellites triangulate position from reactions to artifacts, not captured identity.",
        "deployments": encode(deployments),
        "reads": encode(reads),
        "receipts": encode(factory.receipts),
        "reaction_count": sum(len(d.reactions) for d in deployments),
        "ping_count": sum(len(d.pings) for d in deployments),
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2)
    out.write_text(text)
    js = out.with_name(out.stem + "-data.js")
    js.write_text("window.SATELLITE_DATA = " + text + ";\n")
    print(f"wrote {out} and {js}: {len(deployments)} satellites, {payload['ping_count']} pings, {payload['reaction_count']} reactions")


if __name__ == "__main__":
    main()
