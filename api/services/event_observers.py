# api/services/event_observers.py
# Observer pattern for handling service events

from abc import ABC, abstractmethod


class EventObserver(ABC):
    """Abstract base class for event observers"""

    @abstractmethod
    def handle_event(self, event_type, data):
        """Handle an event"""


class EmailNotificationObserver(EventObserver):
    """Observer for sending email notifications"""

    def handle_event(self, event_type, data):
        """Handle event by sending email notification"""
        from utils.email.email_service import EmailService

        if event_type == "order_created":
            EmailService.send_order_confirmation_email(data["order"])
        elif event_type == "payment_completed":
            EmailService.send_payment_confirmation_email(data["order"])
        elif event_type == "order_status_changed":
            EmailService.send_order_status_update_email(data["order"])
        elif event_type == "review_created":
            EmailService.send_review_notification_email(data["review"])


class CacheInvalidationObserver(EventObserver):
    """Observer for cache invalidation"""

    def handle_event(self, event_type, data):
        """Handle event by invalidating caches"""
        from utils.cache_utils import invalidate_cache_for_instance

        if event_type in ["order_created", "order_updated", "order_deleted"]:
            invalidate_cache_for_instance(data["order"])
        elif event_type in ["service_created", "service_updated", "service_deleted"]:
            invalidate_cache_for_instance(data["service"])
        elif event_type in ["review_created", "review_updated", "review_deleted"]:
            invalidate_cache_for_instance(data["review"])


class EventManager:
    """Event manager for handling observers"""

    def __init__(self):
        self._observers = []

    def register_observer(self, observer: EventObserver):
        """Register an observer"""
        self._observers.append(observer)

    def unregister_observer(self, observer: EventObserver):
        """Unregister an observer"""
        if observer in self._observers:
            self._observers.remove(observer)

    def notify_observers(self, event_type, data):
        """Notify all observers of an event"""
        for observer in self._observers:
            try:
                observer.handle_event(event_type, data)
            except Exception as e:
                # Log error but don't fail
                print(f"Error notifying observer: {e}")
