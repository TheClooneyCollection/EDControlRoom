from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from edap.routing.types import InGameRoute
from edap.spansh_router import SpanshRoute

Verdict = Literal["spansh_better", "in_game_better", "even"]


@dataclass(frozen=True)
class RouteComparison:
    in_game: InGameRoute
    spansh: SpanshRoute
    jumps_delta: int
    neutron_delta: int
    verdict: Verdict
    jump_summary: str
    neutron_summary: str
    tts_phrase: str


def compare(
    in_game: InGameRoute,
    spansh: SpanshRoute,
    *,
    title: str = "Commander",
) -> RouteComparison:
    jumps_delta = spansh.total_jumps - in_game.total_jumps
    neutron_delta = spansh.neutron_count - in_game.neutron_count

    if jumps_delta < 0:
        verdict: Verdict = "spansh_better"
    elif jumps_delta > 0:
        verdict = "in_game_better"
    else:
        verdict = "even"

    jump_summary = _jump_summary(jumps_delta)
    neutron_summary = _neutron_summary(neutron_delta)

    return RouteComparison(
        in_game=in_game,
        spansh=spansh,
        jumps_delta=jumps_delta,
        neutron_delta=neutron_delta,
        verdict=verdict,
        jump_summary=jump_summary,
        neutron_summary=neutron_summary,
        tts_phrase=(
            f"{title}, Spansh route came back and it {jump_summary}, "
            f"{neutron_summary}, would you like to review?"
        ),
    )


def _jump_summary(jumps_delta: int) -> str:
    if jumps_delta < 0:
        return f"saves {abs(jumps_delta)} jumps"
    if jumps_delta > 0:
        return f"adds {jumps_delta} jumps"
    return "matches on jumps"


def _neutron_summary(neutron_delta: int) -> str:
    if neutron_delta > 0:
        return f"with {neutron_delta} more neutron jumps"
    if neutron_delta < 0:
        return f"with {abs(neutron_delta)} fewer neutron jumps"
    return "with the same number of neutron jumps"
