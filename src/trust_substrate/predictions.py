"""Product-level falsifiable predictions SP1-SP5."""
from __future__ import annotations

from .models import ProductPrediction


PREDICTIONS = [
    ProductPrediction(
        "SP1",
        "Directional rejection beats terminal rejection on recovered-fit rate and trust-gap accumulation.",
        "Terminal rejection performs as well as directional routing under matched membrane strictness.",
        "receipt_settlement_rate + recovered_fit_rate",
        "matched wells over first 30 routing receipts",
        "terminal rejection has equal or better recovered-fit and σ accumulation",
    ),
    ProductPrediction(
        "SP2",
        "Synthetic reach scales with corpus diversity.",
        "Synthesis succeeds independently of corpus diversity.",
        "synthetic_fit_success_rate by corpus diversity bucket",
        "first 20 synthetic well receipts",
        "success rate is flat across diversity or succeeds for orthogonal needs equally",
    ),
    ProductPrediction(
        "SP3",
        "Snapshot links go stale faster than live links under acceleration.",
        "Live and snapshot links show equivalent stale-trust incidents.",
        "stale_trust_incidents per settlement interval",
        "first federated link pilot",
        "no difference between live and snapshot links under elevated turnover",
    ),
    ProductPrediction(
        "SP4",
        "A zero-slack membrane field-fakes: σ_s falls while σ_w rises.",
        "No-slack membranes maintain external calibration.",
        "sigma_s/sigma_w divergence",
        "A/B membrane slack pilot",
        "zero-slack membrane keeps σ_w bounded without later false accepts/rejects",
    ),
    ProductPrediction(
        "SP5",
        "Complementarity predicts durable landings.",
        "Parallel and complementary routings settle equally well.",
        "durable settlement by complementarity score",
        "first 50 routing receipts",
        "near-parallel routes settle as durably as complementary routes",
    ),
]


def prediction_registry() -> list[ProductPrediction]:
    return list(PREDICTIONS)
