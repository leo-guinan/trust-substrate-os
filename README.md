Trust Substrate OS
==================

A creator-business operating system that instantiates the σ-trust account of *The Shape of Trust* as a working detection-and-routing federation.

Thesis
------

The system reads only posted events — the deformations a credential leaves on a textured surface. Trust is the carried σ gap between prediction and observation. Rejection is directional and receipt-backed, not terminal. Graduation from apprentice to journeyman is gated by λ, the rate at which predictions actually settle.

What exists now
---------------

| Component | State | Location |
|-----------|-------|----------|
| Core impression engine | Shipped | `src/trust_substrate/engine.py` |
| σ / λ mechanics | Shipped | `src/trust_substrate/sigma.py` |
| Prediction receipts | Shipped | `src/trust_substrate/receipts.py` |
| Capacity seats | Shipped | `src/trust_substrate/capacity.py` |
| Flow queue | Shipped | `src/trust_substrate/flow.py` |
| Graduation workflow | Shipped | `src/trust_substrate/graduation.py` |
| Routing + synthesis stubs | Shipped | `src/trust_substrate/routing.py`, `src/trust_substrate/synthesis.py` |
| Mind Lab sun generator | Shipped | `src/trust_substrate/sun.py` |
| Apprentice flow UI | Shipped | `docs/apprentice-flow.html` |
| Apprentice-facing surface mock | Shipped | `docs/apprentice-surface.html` |
| Tests | 18 passing | `tests/` |

Quickstart
----------

```bash
cd ~/Projects/trust-substrate-os
PYTHONPATH=src python -m pytest tests/ -q
PYTHONPATH=src python scripts/export-flow-snapshot.py --out docs/flow.json
open docs/apprentice-flow.html
open docs/apprentice-surface.html
```

Refresh the Mind Lab sun:

```bash
bash scripts/update-sun.sh ~/Projects/mind-lab docs/sun.json
```

Core concepts
-------------

- **Sun / corpus** = compressed body of work whose density lowers downstream cost.
- **Planet** = landing destination around a corpus.
- **σ_w** = prediction vs posted world-observation gap.
- **σ_s** = prediction vs model self-coherence gap.
- **λ** = disconfirmation cycle rate. Trust grows no faster than λ.
- **Prediction receipt** = a losable claim: route, synthesize, graduate, or review.
- **Flow queue** = operator work sorted by what blocks bounded apprentice/journeyman flow.

Removed from v1
---------------

No tarpit. `Outcome.LOOPED` is gone. A suspected turn now triggers a revocation-review receipt that subsequent posted events can confirm or disconfirm.

Day 0 accuracy: 14%. Published both misses. That's the only reason the hits mean anything.
