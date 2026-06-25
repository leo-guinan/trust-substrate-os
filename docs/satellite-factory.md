# Satellite Factory

Satellites are substrate instruments deployed at a chosen orbit layer. They emit artifacts — tweets, threads, demos, prompts, offers — and measure posted reactions as deformations.

They are not identity-capture devices. A satellite reads a credential's reaction path:

- which artifact caused a response
- what kind of reaction happened
- how specific/contextual the reaction was
- whether the reaction moved with the artifact's grain
- whether the same credential shows consistent bearing across layers

## Why the furthest-edge satellite matters

The outer satellite listens to public pings: tweets sent into the open internet. It is cheap, high-volume, and low-trust. It can detect whether a person is merely recognizing language or actually moving toward artifact use.

A like is a weak deformation. A reply asking for the schema is stronger. A click into the dashboard followed by a case note is stronger still. The satellite triangulates position from the sequence.

## Deployment layers

| Layer | Orbit | Use |
|---|---:|---|
| edge | 1.00 | public tweets / pings |
| visitor | 0.82 | weak contact, no seat |
| apprentice | 0.58 | apprentice artifacts and case notes |
| journeyman | 0.24 | collaboration probes |
| federation | 0.42 | cross-well altitude recognition |

## Product rule

A satellite can inform orbit and σ, but it cannot by itself promote someone. Promotion still requires settled receipts and λ. The satellite gives bearings; the ladder decides standing.

## Current implementation

- Domain: `src/trust_substrate/satellites.py`
- Fake cohort: `src/trust_substrate/satellite_fakes.py`
- Snapshot export: `scripts/export-satellite-snapshot.py`
- UI: `docs/satellite-factory.html`

Generate snapshot:

```bash
PYTHONPATH=src python scripts/export-satellite-snapshot.py --out docs/satellites.json
open docs/satellite-factory.html
```

## Future live X integration

The write path must remain explicit-approval gated. The satellite factory should ingest tweet IDs/URLs and read reaction metrics after posting. It should not autonomously post pings until the campaign has a pre-registered prediction and approval boundary.
