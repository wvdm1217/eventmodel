"""
EventModel: A type-driven, zero-boilerplate event framework.
"""
from eventmodel.models import EventModel
from eventmodel.service import Service
from eventmodel.app import App

__all__ = ["EventModel", "Service", "App"]
