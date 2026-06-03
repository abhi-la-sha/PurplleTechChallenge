from app.repositories.metrics import MetricsRepository
from app.schemas.metrics import (
    FunnelResponse,
    FunnelStage,
    HeatmapResponse,
    HeatmapZone,
    MetricsResponse,
    StoreMetricsResponse,
)

_DATA_CONFIDENCE_THRESHOLD = 20


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


    async def get_store_funnel(self, store_id: str) -> FunnelResponse:
        counts = await self._repository.get_funnel_stage_counts(store_id)

        stage_definitions = [
            ("Entry", counts["entry"]),
            ("Zone Visit", counts["zone_visit"]),
            ("Billing Queue", counts["billing_queue"]),
            ("Purchase", counts["purchase"]),
        ]

        stages: list[FunnelStage] = []
        for i, (label, count) in enumerate(stage_definitions):
            if i == 0:
                drop_off_pct = 0.0
            else:
                prev_count = stage_definitions[i - 1][1]
                if prev_count > 0:
                    drop_off_pct = round(
                        ((prev_count - count) / prev_count) * 100, 2
                    )
                else:
                    drop_off_pct = 0.0
            stages.append(
                FunnelStage(
                    stage=label,
                    count=count,
                    drop_off_from_previous_pct=drop_off_pct,
                )
            )

        return FunnelResponse(store_id=store_id, stages=stages)


    async def get_store_heatmap(self, store_id: str) -> HeatmapResponse:
        visit_counts = await self._repository.get_zone_visit_counts(store_id)
        avg_dwell_map = await self._repository.get_zone_avg_dwell_ms(store_id)
        total_unique_visitors = await self._repository.get_store_unique_visitor_count(
            store_id
        )

        data_confidence = total_unique_visitors >= _DATA_CONFIDENCE_THRESHOLD

        if not visit_counts:
            return HeatmapResponse(
                store_id=store_id,
                zones=[],
                data_confidence=data_confidence,
            )

        max_visits = visit_counts[0][1]  # already ordered desc

        zones: list[HeatmapZone] = []
        for zone_name, count in visit_counts:
            avg_dwell_ms = avg_dwell_map.get(zone_name, 0.0)
            normalised = round((count / max_visits) * 100, 2) if max_visits > 0 else 0.0
            zones.append(
                HeatmapZone(
                    zone_id=zone_name,
                    visit_count=count,
                    avg_dwell_seconds=round(avg_dwell_ms / 1000, 2),
                    normalised_score=normalised,
                )
            )

        return HeatmapResponse(
            store_id=store_id,
            zones=zones,
            data_confidence=data_confidence,
        )


def _round_or_zero(value: float | None) -> float:
    if value is None:
        return 0.0
    return round(float(value), 2)