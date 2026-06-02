
from app.repositories.metrics import MetricsRepository
from app.schemas.metrics import MetricsResponse


class MetricsService:
    

    def __init__(self, repository: MetricsRepository) -> None:
        self._repository = repository

    async def get_metrics(self) -> MetricsResponse:
        total_visitors = await self._repository.get_total_visitors()
        converted_visitors = await self._repository.get_converted_visitors()
        avg_dwell = await self._repository.get_average_dwell_time()
        avg_basket = await self._repository.get_average_basket_value()

        conversion_rate = 0.0
        if total_visitors > 0:
            conversion_rate = round((converted_visitors / total_visitors) * 100, 2)

        return MetricsResponse(
            total_visitors=total_visitors,
            converted_visitors=converted_visitors,
            conversion_rate=conversion_rate,
            average_dwell_time_seconds=_round_or_zero(avg_dwell),
            average_basket_value=_round_or_zero(avg_basket),
        )


def _round_or_zero(value: float | None) -> float:
    if value is None:
        return 0.0
    return round(float(value), 2)
