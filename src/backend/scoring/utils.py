"""Small numeric helpers shared by scoring modules."""

from collections.abc import Sequence
from statistics import mean

from ..models.scoring import Component, Score


def clamp(value: float) -> float:
    """Keep a score inside the public 0-100 range."""

    return round(max(0.0, min(100.0, value)), 2)


def average(values: Sequence[float | None]) -> float | None:
    """Average available values without treating missing evidence as zero."""

    present = [value for value in values if value is not None]
    return clamp(mean(present)) if present else None


def weighted(
    components: list[Component],
    *,
    require_all: bool = False,
) -> Score:
    """Combine available components and preserve every component as evidence."""

    available = [component for component in components if component.value is not None]
    value: float | None = None

    if available and (not require_all or len(available) == len(components)):
        weighted_total = sum(
            component.value * component.weight
            for component in available
            if component.value is not None
        )
        total_weight = sum(component.weight for component in available)
        value = clamp(weighted_total / total_weight)

    reason = (
        None
        if len(available) == len(components)
        else "Unavailable components; see component reasons"
    )

    return Score(value=value, components=components, reason=reason)
