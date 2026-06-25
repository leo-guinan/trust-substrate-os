"""Canonical textured surfaces."""
from __future__ import annotations

from .models import SurfaceTexture, ZoneGrain


def mind_lab_surface(well_id: str = "mind_lab") -> SurfaceTexture:
    return SurfaceTexture(
        well_id=well_id,
        zones={
            "orientation": ZoneGrain("orientation", {"reads_foundation": 0.9, "skims_extracts": 0.25}, 0.8, 0.2),
            "translation": ZoneGrain("translation", {"restate_in_own_context": 0.9, "asks_generic_summary": 0.35}, 1.4, 0.4),
            "application": ZoneGrain("application", {"specific_case_analysis": 0.92, "asks_for_template": 0.45, "extracts_prompt_pack": 0.15}, 2.2, 0.6),
            "contribution": ZoneGrain("contribution", {"adds_artifact": 0.9, "asks_for_access": 0.2}, 3.0, 0.8),
            "well_design": ZoneGrain("well_design", {"designs_own_well": 0.95, "copies_operator": 0.35}, 3.5, 0.9),
            "journeyman_edge": ZoneGrain("journeyman_edge", {"operates_with_scaffold": 0.9, "needs_constant_rescue": 0.25}, 4.0, 1.0),
        },
        decay_half_life_hours=72.0,
    )
