from datetime import datetime, timezone

from app.repositories.metrics import MetricsRepository
from app.schemas.metrics import (
    AnomaliesResponse,
    AnomalyItem,
    FunnelResponse,
    FunnelStage,
    HeatmapResponse,
    HeatmapZone,
    MetricsResponse,
    StoreMetricsResponse,
)

_DATA_CONFIDENCE_THRESHOLD = 20

_QUEUE_WARN = 5
_QUEUE_CRITICAL = 10

_CONVERSION_DROP_WARN = 0.20    
_CONVERSION_DROP_CRITICAL = 0.40  
_CONVERSION_MIN_VISITORS = 5      

def _round_or_zero(value: float | None) -> float:
    if value is None:
        return 0.0
    return round(value, 2)
    
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

        return StoreMetricsResponse(
            store_id=store_id,
            unique_visitors=unique_visitors,
            converted_visitors=converted_visitors,
            conversion_rate=conversion_rate,
            average_dwell_time_seconds=_round_or_zero(
                avg_dwell_ms / 1000 if avg_dwell_ms else None
            ),
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
                prev = stage_definitions[i - 1][1]
                drop_off_pct = round(((prev - count) / prev) * 100, 2) if prev > 0 else 0.0
            stages.append(
                FunnelStage(stage=label, count=count, drop_off_from_previous_pct=drop_off_pct)
            )
        return FunnelResponse(store_id=store_id, stages=stages)


    async def get_store_heatmap(self, store_id: str) -> HeatmapResponse:
        visit_counts = await self._repository.get_zone_visit_counts(store_id)
        avg_dwell_map = await self._repository.get_zone_avg_dwell_ms(store_id)
        total_unique = await self._repository.get_store_unique_visitor_count(store_id)

        data_confidence = total_unique >= _DATA_CONFIDENCE_THRESHOLD

        if not visit_counts:
            return HeatmapResponse(
                store_id=store_id, zones=[], data_confidence=data_confidence
            )

        max_visits = visit_counts[0][1]
        zones = [
            HeatmapZone(
                zone_id=zone_name,
                visit_count=count,
                avg_dwell_seconds=round(avg_dwell_map.get(zone_name, 0.0) / 1000, 2),
                normalised_score=round((count / max_visits) * 100, 2) if max_visits > 0 else 0.0,
            )
            for zone_name, count in visit_counts
        ]
        return HeatmapResponse(
            store_id=store_id, zones=zones, data_confidence=data_confidence
        )


    async def get_store_anomalies(self, store_id: str) -> AnomaliesResponse:
        now = datetime.now(timezone.utc)
        anomalies: list[AnomalyItem] = []

        queue_depth = await self._repository.get_store_queue_depth(store_id)

        if queue_depth >= _QUEUE_CRITICAL:
            anomalies.append(AnomalyItem(
                anomaly_type="BILLING_QUEUE_SPIKE",
                severity="CRITICAL",
                description=f"Billing queue depth is critically high at {queue_depth}.",
                suggested_action=(
                    "Deploy additional staff to billing counters immediately "
                    "and open all available POS terminals."
                ),
                detected_at=now,
            ))
        elif queue_depth >= _QUEUE_WARN:
            anomalies.append(AnomalyItem(
                anomaly_type="BILLING_QUEUE_SPIKE",
                severity="WARN",
                description=f"Billing queue depth is elevated at {queue_depth}.",
                suggested_action="Open an additional billing counter to reduce wait time.",
                detected_at=now,
            ))
        elif queue_depth >= 3:
            anomalies.append(AnomalyItem(
                anomaly_type="BILLING_QUEUE_SPIKE",
                severity="INFO",
                description=f"Billing queue depth is {queue_depth}.",
                suggested_action="Monitor billing queue — may grow further during peak hours.",
                detected_at=now,
            ))

    
        rate_data = await self._repository.get_conversion_rates(store_id)
        today_visitors = rate_data["today_visitors"]
        today_rate = rate_data["today_rate"]
        historical_visitors = rate_data["historical_visitors"]
        historical_rate = rate_data["historical_rate"]

        if (
            today_visitors >= _CONVERSION_MIN_VISITORS
            and historical_visitors >= _CONVERSION_MIN_VISITORS
            and historical_rate > 0
        ):
            relative_drop = (historical_rate - today_rate) / historical_rate

            if relative_drop >= _CONVERSION_DROP_CRITICAL:
                anomalies.append(AnomalyItem(
                    anomaly_type="CONVERSION_DROP",
                    severity="CRITICAL",
                    description=(
                        f"Today's conversion rate ({today_rate:.1f}%) is "
                        f"{relative_drop * 100:.0f}% below the 7-day average "
                        f"({historical_rate:.1f}%)."
                    ),
                    suggested_action=(
                        "Investigate checkout friction immediately. "
                        "Check for POS failures, pricing anomalies, or product availability issues."
                    ),
                    detected_at=now,
                ))
            elif relative_drop >= _CONVERSION_DROP_WARN:
                anomalies.append(AnomalyItem(
                    anomaly_type="CONVERSION_DROP",
                    severity="WARN",
                    description=(
                        f"Today's conversion rate ({today_rate:.1f}%) is "
                        f"{relative_drop * 100:.0f}% below the 7-day average "
                        f"({historical_rate:.1f}%)."
                    ),
                    suggested_action=(
                        "Review floor staff availability and customer journey. "
                        "Check if high-traffic zones are well stocked."
                    ),
                    detected_at=now,
                ))

        dead_zones = await self._repository.get_dead_zones(store_id, lookback_minutes=30)

        for zone_name in dead_zones:
            anomalies.append(AnomalyItem(
                anomaly_type="DEAD_ZONE",
                severity="INFO",
                description=(
                    f"Zone '{zone_name}' has had no visitor activity for 30+ minutes "
                    "despite the store being active."
                ),
                suggested_action=(
                    f"Check zone '{zone_name}' — consider repositioning merchandise, "
                    "improving signage, or deploying a staff member to engage customers."
                ),
                detected_at=now,
            ))

        return AnomaliesResponse(store_id=store_id, anomalies=anomalies)