
from fastapi import APIRouter

from app.api.routes import (
    anomalies,
    events,
    funnel,
    health,
    heatmap,
    metrics,
    root,
    transactions,
)

api_router = APIRouter()
api_router.include_router(root.router)
api_router.include_router(health.router)
api_router.include_router(events.router)
api_router.include_router(metrics.router)
api_router.include_router(transactions.router)
api_router.include_router(funnel.router)
api_router.include_router(anomalies.router)
api_router.include_router(heatmap.router)
