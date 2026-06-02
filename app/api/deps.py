
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_async_session
from app.repositories.event import EventRepository
from app.repositories.health import HealthRepository
from app.repositories.metrics import MetricsRepository
from app.repositories.transaction import TransactionRepository
from app.services.event import EventService
from app.services.health import HealthService
from app.services.metrics import MetricsService
from app.services.transaction import TransactionService
from app.services.placeholder import PlaceholderService
from app.services.root import RootService

SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[AsyncSession, Depends(get_async_session)]


def get_health_repository(session: SessionDep) -> HealthRepository:
    return HealthRepository(session)


HealthRepositoryDep = Annotated[HealthRepository, Depends(get_health_repository)]


def get_health_service(repository: HealthRepositoryDep) -> HealthService:
    return HealthService(repository)


HealthServiceDep = Annotated[HealthService, Depends(get_health_service)]


def get_root_service(settings: SettingsDep) -> RootService:
    return RootService(settings)


RootServiceDep = Annotated[RootService, Depends(get_root_service)]


def get_placeholder_service() -> PlaceholderService:
    return PlaceholderService()


PlaceholderServiceDep = Annotated[PlaceholderService, Depends(get_placeholder_service)]


def get_event_repository(session: SessionDep) -> EventRepository:
    return EventRepository(session)


EventRepositoryDep = Annotated[EventRepository, Depends(get_event_repository)]


def get_event_service(repository: EventRepositoryDep) -> EventService:
    return EventService(repository)


EventServiceDep = Annotated[EventService, Depends(get_event_service)]


def get_metrics_repository(session: SessionDep) -> MetricsRepository:
    return MetricsRepository(session)


MetricsRepositoryDep = Annotated[MetricsRepository, Depends(get_metrics_repository)]


def get_metrics_service(repository: MetricsRepositoryDep) -> MetricsService:
    return MetricsService(repository)


MetricsServiceDep = Annotated[MetricsService, Depends(get_metrics_service)]


def get_transaction_repository(session: SessionDep) -> TransactionRepository:
    return TransactionRepository(session)


TransactionRepositoryDep = Annotated[
    TransactionRepository,
    Depends(get_transaction_repository),
]


def get_transaction_service(repository: TransactionRepositoryDep) -> TransactionService:
    return TransactionService(repository)


TransactionServiceDep = Annotated[TransactionService, Depends(get_transaction_service)]
