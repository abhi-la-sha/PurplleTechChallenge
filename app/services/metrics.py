from app.repositories.metrics import MetricsRepository
from app.schemas.metrics import MetricsResponse, StoreMetricsResponse


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

    async def get_store_metrics(self, store_id: str) -> StoreMetricsResponse:
        unique_visitors = await self._repository.get_store_unique_visitors(store_id)
        converted_visitors = await self._repository.get_store_converted_visitors(store_id)
        avg_dwell_ms = await self._repository.get_store_average_dwell_ms(store_id)
        queue_depth = await self._repository.get_store_queue_depth(store_id)
        abandoned, joined = await self._repository.get_store_abandonment_counts(store_id)
        avg_basket = await self._repository.get_store_average_basket_value(store_id)

        conversion_rate = 0.0
        if unique_visitors > 0:
            conversion_rate = round((converted_visitors / unique_visitors) * 100, 2)

        abandonment_rate = 0.0
        if joined > 0:
            abandonment_rate = round((abandoned / joined) * 100, 2)

        avg_dwell_seconds = 0.0
        if avg_dwell_ms is not None:
            avg_dwell_seconds = round(avg_dwell_ms / 1000, 2)

        return StoreMetricsResponse(
            store_id=store_id,
            unique_visitors=unique_visitors,
            converted_visitors=converted_visitors,
            conversion_rate=conversion_rate,
            average_dwell_time_seconds=avg_dwell_seconds,
            queue_depth=queue_depth,
            abandonment_rate=abandonment_rate,
            average_basket_value=_round_or_zero(avg_basket),
        )


def _round_or_zero(value: float | None) -> float:
    if value is None:
        return 0.0
    return round(float(value), 2)