Trust Substrate OS
==================

A creator-business operating system built as a detection-and-routing network, not a capture funnel.

Thesis
------

Most audience-building tools maximize capture: pull in as many people as possible, harvest contact info, sort later. This system inverts that. It is a **capacity-bounded detection and filtration network** whose core job is *cheap, early, correct rejection* — letting the wrong people pass quickly so the most energy is left for the right ones.

Build priority
--------------

1. **Scoring/impression engine** (this package) — maps observed behavior → orbital radius and geodesic.
2. Textured apprentice surface (chatbot interface).
3. Path-credential primitive.
4. Membrane gates (starting over-tight for cold-start).
5. Internal immune response (honeypot branches).
6. Wormhole handshake + referral trust ledger.

Status
------

| Component | State | Location |
|-----------|-------|----------|
| Core engine | Shipped | `src/trust_substrate/engine.py` |
| Data models | Shipped | `src/trust_substrate/models.py` |
| Gate logic | Shipped | `src/trust_substrate/gates.py` |
| Tests | 7 passing | `tests/test_engine.py` |

Quickstart
----------

```bash
cd ~/Projects/trust-substrate-os
pip install -r requirements.txt
pytest tests/
```

Core concept: the surface
-------------------------

- **Orbit** = sum of recent energy spent toward the well, decaying in real time.
- **Geodesic** = the lowest-energy route an actor takes across a textured surface; selection is the verdict.
- **Grain** = the route the surface affords. With-grain = aligned with the lens; against-grain = bent toward extraction.

The three gates
---------------

| Gate | Question | Cost | Action |
|------|----------|------|--------|
| G0 | Intent or drift? | ~0 | Reject bots/scrapers/noise |
| G1 | Extractive? | low | Reject pitch-bots/harvesters |
| G2 | This well's grain? | higher | Route misfits to wormhole; accept fits |

Day 0 accuracy: 14%. Published both misses. That's the only reason the hits mean anything.
