# Shape of Trust Reconciliation

Trust Substrate OS is downstream of *The Shape of Trust*. Product loses to paper.

## Mechanism map

| Product mechanism | Paper claim |
|---|---|
| σ_w / σ_s state | trust as carried prediction-observation gap; coupled world/self loops |
| PredictionReceipt | committed claim before settlement; receipt survives compression |
| λ rate | trust grows no faster than disconfirmation cycles settle |
| Directional routing | rejection transfers the gap instead of zeroing it |
| Provisional synthesis | no-fit events reveal representational slack gaps |
| Capacity seats | sampling capacity bounds honest trust-gap carrying |
| Flow queue | operator work sorted by what blocks bounded flow |

## Cut from v1

Tarpit/honeypot is removed from the domain model. `Outcome.LOOPED` no longer exists. Automated turn response is now a revocation-review receipt that can be confirmed or disconfirmed by subsequent posted events.

## Changed from v1

Terminal rejection is no longer the default model. Gate 2 misfit can produce a routing receipt. Manual ejection remains as an operator override, but the automated path is losable review/routing.

## New load-bearing constraint

Graduation is gated by λ. A candidate can have low σ_w and high apparent fit, but if receipts have not settled, the system cannot honestly promote them. Confidence-before-calibration is the bug this product exists to measure.

## Current stubs

- Corpus diversity is not yet computed; synthetic reach is represented as low-confidence provisional specs.
- Federation links are not implemented; routing uses local WellSignature fixtures.
- UI uses exported JSON snapshots, not a live API.
