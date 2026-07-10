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

    return RouteComparison(
        in_game=in_game,
        spansh=spansh,
        jumps_delta=jumps_delta,
        neutron_delta=neutron_delta,
        verdict=verdict,
        tts_phrase=_build_tts_phrase(
            title=title,
            jumps_delta=jumps_delta,
            neutron_delta=neutron_delta,
        ),
    )


def _build_tts_phrase(*, title: str, jumps_delta: int, neutron_delta: int) -> str:
    if jumps_delta < 0:
        jumps_part = f"saves {abs(jumps_delta)} jumps"
    elif jumps_delta > 0:
        jumps_part = f"adds {jumps_delta} jumps"
    else:
        jumps_part = "matches on jumps"

    if neutron_delta > 0:
        neutron_part = f"with {neutron_delta} more neutron jumps"
    elif neutron_delta < 0:
        neutron_part = f"with {abs(neutron_delta)} fewer neutron jumps"
    else:
        neutron_part = "with the same number of neutron jumps"

    return (
        f"{title}, Spansh route came back and it {jumps_part}, "
        f"{neutron_part}, would you like to review?"
    )
