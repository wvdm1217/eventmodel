"""
EventModel: A type-driven, zero-boilerplate event framework.
"""

from eventmodel.app import App
from eventmodel.broker import Broker
from eventmodel.brokers.asyncio_broker import AsyncioBroker
from eventmodel.config import settings
from eventmodel.logger import logger
from eventmodel.models import (
    AlwaysEvent,
    EventModel,
    StartEvent,
    StopEvent,
    SystemEvent,
)
from eventmodel.service import Service
from eventmodel.tracing import get_tracer

__all__ = [
    "EventModel",
    "SystemEvent",
    "StartEvent",
    "AlwaysEvent",
    "StopEvent",
    "Service",
    "App",
    "Broker",
    "AsyncioBroker",
    "logger",
    "settings",
    "get_tracer",
]
